"""
Native Z-Image Pipeline.

This module provides a complete image generation pipeline for Z-Image
without diffusers dependency, supporting FP8 scaled checkpoints.
"""

from __future__ import annotations

import gc
import os
import numpy as np
from PIL import Image
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from safetensors import safe_open
from safetensors.torch import load_file as load_safetensors

from airunner.components.art.managers.zimage.native.fp8_ops import (
    FP8Linear,
    UnscaledFP8Linear,
    QuantizedTensor,
    TensorCoreFP8Layout,
    is_fp8_scaled_checkpoint,
)
from airunner.components.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)
from airunner.components.art.managers.zimage.native.nextdit_model import (
    NextDiT,
    ZIMAGE_CONFIG,
    create_zimage_transformer,
)
from airunner.components.art.managers.zimage.native.zimage_text_encoder import (
    ZImageTextEncoder,
    ZImageTokenizer,
)
# We still rely on diffusers AutoencoderKL until a native VAE is available.
from diffusers import AutoencoderKL

logger = logging.getLogger(__name__)


class _NativeVaeImageProcessor:
    """Lightweight VAE image processor to avoid diffusers dependency."""

    def __init__(self, vae_scale_factor: int = 8):
        self.vae_scale_factor = vae_scale_factor

    def _ensure_multiple(self, value: int) -> int:
        if self.vae_scale_factor <= 0:
            return value
        return int(value // self.vae_scale_factor * self.vae_scale_factor)

    def preprocess(self, image: Union[Image.Image, List[Image.Image], torch.Tensor], height: int, width: int) -> torch.Tensor:
        """Resize and normalize to [-1, 1] torch tensor batch."""
        if isinstance(image, torch.Tensor):
            # Assume already normalized/reshaped (B, C, H, W)
            return image

        images = image if isinstance(image, list) else [image]
        target_h = self._ensure_multiple(height)
        target_w = self._ensure_multiple(width)

        tensors: List[torch.Tensor] = []
        for img in images:
            if not isinstance(img, Image.Image):
                raise ValueError("Expected PIL Image for preprocess")
            img = img.convert("RGB")
            img = img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)
            arr = np.array(img).astype(np.float32) / 255.0  # HWC, [0,1]
            arr = torch.from_numpy(arr).permute(2, 0, 1)  # CHW
            arr = arr * 2.0 - 1.0
            tensors.append(arr)

        return torch.stack(tensors, dim=0)


def set_module_tensor_to_device(
    module: nn.Module,
    tensor_name: str,
    device: Union[str, torch.device],
    value: torch.Tensor,
) -> None:
    """
    Set a tensor on a module, handling nested attribute access.
    
    Args:
        module: Target module
        tensor_name: Dot-separated path to tensor (e.g., "layers.0.weight")
        device: Target device
        value: Tensor value to set
    """
    parts = tensor_name.split(".")
    
    # Navigate to parent module
    for part in parts[:-1]:
        if part.isdigit():
            module = module[int(part)]
        else:
            module = getattr(module, part)
    
    # Set the tensor
    param_name = parts[-1]
    
    # Move value to device if it's not a QuantizedTensor
    if not isinstance(value, QuantizedTensor):
        value = value.to(device)
    
    if hasattr(module, param_name):
        delattr(module, param_name)
    
    if isinstance(value, QuantizedTensor):
        # For quantized tensors, store as buffer
        module.register_buffer(param_name, value._qdata)
        # Store scale separately
        scale_name = f"{param_name}_scale"
        module.register_buffer(scale_name, value._layout_params['scale'])
    else:
        # Regular parameter
        setattr(module, param_name, nn.Parameter(value, requires_grad=False))


class ZImageNativePipeline:
    """
    Native Z-Image pipeline for image generation.
    
    This pipeline handles:
    - FP8 checkpoint loading with streaming
    - Text encoding with Qwen
    - Flow matching sampling
    - VAE decoding
    
    Args:
        transformer_path: Path to transformer checkpoint (FP8 or regular)
        text_encoder_path: Path to text encoder model
        vae_path: Path to VAE model
        device: Target device
        dtype: Compute dtype (bfloat16 recommended)
        text_encoder_quantization: Quantization for text encoder ("4bit", "8bit", None)
    """
    
    def __init__(
        self,
        transformer_path: Optional[str] = None,
        text_encoder_path: Optional[str] = None,
        vae_path: Optional[str] = None,
        device: Optional[torch.device] = None,
        dtype: torch.dtype = torch.bfloat16,
        text_encoder_quantization: Optional[str] = "4bit",
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        elif isinstance(device, str):
            self.device = torch.device(device)
        else:
            self.device = device
        self.dtype = dtype
        self.text_encoder_quantization = text_encoder_quantization
        self.image_processor: Optional[_NativeVaeImageProcessor] = None
        
        # Components
        self.transformer: Optional[NextDiT] = None
        self.text_encoder: Optional[ZImageTextEncoder] = None
        self.tokenizer: Optional[ZImageTokenizer] = None
        self.vae: Optional[nn.Module] = None
        self.scheduler: Optional[FlowMatchEulerScheduler] = None
        
        # Paths
        self.transformer_path = transformer_path
        self.text_encoder_path = text_encoder_path
        self.vae_path = vae_path
        
        # State
        self.is_fp8 = False
        self._loaded_components: List[str] = []

    @property
    def components(self) -> Dict[str, Any]:
        """Diffusers-style components mapping used by PEFT loaders."""
        comps: Dict[str, Any] = {
            "transformer": self.transformer,
            "text_encoder": self.text_encoder,
            "tokenizer": self.tokenizer,
            "vae": self.vae,
            "scheduler": self.scheduler,
        }
        return {k: v for k, v in comps.items() if v is not None}
    
    @property
    def memory_usage(self) -> Dict[str, float]:
        """Get current memory usage in GB."""
        if not torch.cuda.is_available():
            return {"vram": 0, "cpu": 0}
        
        vram = torch.cuda.memory_allocated() / 1024**3
        cpu = torch.cuda.memory_reserved() / 1024**3  # Approximation

        # PEFT compatibility: diffusers LoRA loader checks hf_device_map
        # even though native pipeline manages devices internally.
        self.hf_device_map = None
        
        return {"vram": vram, "cpu": cpu}
    
    def load_transformer(
        self,
        checkpoint_path: Optional[str] = None,
        stream_load: bool = True,
    ) -> None:
        """
        Load the transformer from checkpoint.
        
        Supports both FP8 scaled checkpoints and regular checkpoints.
        
        Args:
            checkpoint_path: Path to checkpoint file
            stream_load: Whether to stream load (memory efficient)
        """
        path = checkpoint_path or self.transformer_path
        if path is None:
            raise ValueError("No transformer path provided")
        
        logger.info(f"Loading transformer from {path}")
        
        # Check if FP8 checkpoint (scaled or unscaled)
        self._is_unscaled_fp8 = False
        if path.endswith('.safetensors'):
            has_fp8_dtype = False
            has_scale_key = False
            with safe_open(path, framework='pt') as f:
                all_keys = list(f.keys())
                # Check for scale_weight keys anywhere
                has_scale_key = any('scale_weight' in k for k in all_keys)
                # Sample tensor dtypes
                for i, key in enumerate(all_keys):
                    if i > 50:
                        break
                    t = f.get_tensor(key)
                    if t.dtype == torch.float8_e4m3fn:
                        has_fp8_dtype = True
                        break
            
            # Scaled FP8 = has FP8 dtype AND scale weights
            self.is_fp8 = has_fp8_dtype and has_scale_key
            # Unscaled FP8 = has FP8 dtype but NO scale weights
            self._is_unscaled_fp8 = has_fp8_dtype and not has_scale_key
        
        if self._is_unscaled_fp8:
            logger.info(f"Checkpoint is unscaled FP8 (will cast to {self.dtype})")
        else:
            logger.info(f"Checkpoint is FP8 scaled: {self.is_fp8}")
        
        if self.is_fp8 and stream_load:
            self._load_fp8_checkpoint_streaming(path)
        else:
            self._load_checkpoint_direct(path)
        
        self._loaded_components.append("transformer")
        logger.info("Transformer loaded successfully")
    
    def _detect_layer_count(self, path: str) -> int:
        """
        Detect the number of transformer layers in a checkpoint.
        
        Args:
            path: Path to safetensors checkpoint
            
        Returns:
            Number of layers found in checkpoint
        """
        layer_nums = set()
        with safe_open(path, framework='pt') as f:
            for key in f.keys():
                if 'layers.' in key:
                    parts = key.split('.')
                    for i, p in enumerate(parts):
                        if p == 'layers' and i + 1 < len(parts):
                            try:
                                layer_nums.add(int(parts[i + 1]))
                            except ValueError:
                                pass
        
        if not layer_nums:
            # Default to config value if no layers found
            return ZIMAGE_CONFIG.get('n_layers', 32)
        
        return len(layer_nums)
    
    def _load_fp8_checkpoint_streaming(self, path: str) -> None:
        """
        Stream load FP8 checkpoint to minimize memory usage.
        
        Keeps weights in FP8 format on GPU for ~50% memory savings.
        Dequantization happens on-the-fly during forward pass.
        
        Args:
            path: Path to safetensors checkpoint
        """
        # FP8Linear is imported at module level; avoid re-importing here.
        
        # First, detect the number of layers from checkpoint
        n_layers = self._detect_layer_count(path)
        logger.info(f"Detected {n_layers} layers in checkpoint")
        
        # Create model config, overriding n_layers if different
        model_config = ZIMAGE_CONFIG.copy()
        if n_layers != model_config.get('n_layers', 32):
            logger.info(f"Overriding n_layers from {model_config.get('n_layers', 32)} to {n_layers}")
            model_config['n_layers'] = n_layers
        
        # Create model structure on meta device (no memory allocation)
        self.transformer = NextDiT(
            **model_config,
            device=torch.device('meta'),
            dtype=self.dtype,
        )
        
        # Collect all weights first
        scale_dict: Dict[str, torch.Tensor] = {}
        all_weights: Dict[str, torch.Tensor] = {}
        
        with safe_open(path, framework='pt') as f:
            keys = list(f.keys())
            
            # First pass: collect scales
            for key in keys:
                if 'scale_weight' in key:
                    scale_dict[key] = f.get_tensor(key)
            
            logger.info(f"Found {len(scale_dict)} scale weights")
            
            # Second pass: load all weights (stays in CPU memory from safetensors mmap)
            for key in keys:
                if 'scale_weight' in key:
                    continue
                all_weights[key] = f.get_tensor(key)
        
        # Track FP8 weights and their layers
        fp8_layers: Dict[str, Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]] = {}
        
        # Collect biases separately (they may appear before weights in iteration)
        bias_dict: Dict[str, torch.Tensor] = {}
        
        # First pass: collect FP8 weights and biases
        for key, tensor in all_weights.items():
            model_key = self._convert_checkpoint_key(key)
            if model_key is None:
                continue
            
            # Collect biases for later association with FP8 layers
            if key.endswith('.bias'):
                parts = model_key.split('.')
                layer_key = '.'.join(parts[:-1])
                bias_dict[layer_key] = tensor
                continue
            
            scale_key = key.replace('.weight', '.scale_weight')
            scale = scale_dict.get(scale_key)
            
            # Check if this is an FP8 weight
            if tensor.dtype == torch.float8_e4m3fn and scale is not None:
                # Track for FP8Linear replacement later
                parts = model_key.split('.')
                if parts[-1] == 'weight':
                    layer_key = '.'.join(parts[:-1])
                    fp8_layers[layer_key] = (tensor, scale, None)  # bias will be added later
            else:
                # Non-FP8 weight: materialize directly on GPU
                try:
                    set_module_tensor_to_device(
                        self.transformer, model_key, self.device,
                        tensor.to(dtype=self.dtype)
                    )
                except Exception as e:
                    logger.debug(f"Could not set {model_key}: {e}")
        
        # Second pass: associate biases with FP8 layers
        for layer_key, bias in bias_dict.items():
            if layer_key in fp8_layers:
                fp8_data, fp8_scale, _ = fp8_layers[layer_key]
                fp8_layers[layer_key] = (fp8_data, fp8_scale, bias)
        
        logger.info(f"Found {len(bias_dict)} biases, {len([k for k, v in fp8_layers.items() if v[2] is not None])} associated with FP8 layers")
        
        # Clean up weight dict to free CPU memory
        del all_weights
        gc.collect()
        
        # Now replace Linear layers with FP8Linear
        replaced = 0
        for layer_key, (fp8_weight, scale, bias) in fp8_layers.items():
            try:
                # Navigate to parent module
                parts = layer_key.split('.')
                parent = self.transformer
                for part in parts[:-1]:
                    parent = getattr(parent, part)
                
                layer_name = parts[-1]
                linear = getattr(parent, layer_name)
                
                if isinstance(linear, nn.Linear) or hasattr(linear, 'in_features'):
                    # Create FP8Linear replacement
                    in_features = fp8_weight.shape[1]
                    out_features = fp8_weight.shape[0]
                    has_bias = bias is not None
                    
                    fp8_linear = FP8Linear(
                        in_features,
                        out_features,
                        bias=has_bias,
                        device=self.device,
                        compute_dtype=self.dtype,
                    )
                    
                    # Set FP8 weight (keep as FP8 on GPU)
                    fp8_linear.set_fp8_weight(
                        fp8_weight.to(self.device),
                        scale.to(self.device)
                    )
                    
                    # Copy bias if present
                    if has_bias:
                        fp8_linear.bias.data.copy_(bias.to(dtype=self.dtype, device=self.device))
                    
                    # Replace the layer
                    setattr(parent, layer_name, fp8_linear)
                    replaced += 1
                    
            except Exception as e:
                logger.warning(f"Failed to replace {layer_key} with FP8Linear: {e}")
        
        logger.info(f"Replaced {replaced} Linear layers with FP8Linear")
        
        # Free remaining CPU memory
        del fp8_layers
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.transformer.eval()
        
        self.transformer.eval()
    
    def _load_checkpoint_direct(self, path: str) -> None:
        """
        Load unscaled FP8 checkpoint directly to GPU.
        
        Keeps weights in FP8 format (~5.4GB for this model).
        FP8->bfloat16 conversion happens on-the-fly during forward pass.
        
        Args:
            path: Path to checkpoint file
        """
        # UnscaledFP8Linear is imported at module level; avoid re-importing here.
        
        # Log pre-load VRAM state
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            logger.info(f"_load_checkpoint_direct: Pre-load VRAM: {allocated:.2f}GB allocated")
        
        # Create model on meta device (0 memory allocation)
        self.transformer = create_zimage_transformer(
            device=torch.device('meta'),
            dtype=self.dtype,
        )
        
        # Collect FP8 layer info and non-FP8 tensors from checkpoint
        fp8_layers = {}  # layer_key -> (weight, bias)
        non_fp8_weights = {}  # model_key -> tensor (on GPU)
        
        with safe_open(path, framework='pt') as f:
            keys = list(f.keys())
            
            for key in keys:
                model_key = self._convert_checkpoint_key(key)
                if model_key is None:
                    continue
                
                tensor = f.get_tensor(key)
                
                if tensor.dtype == torch.float8_e4m3fn:
                    # FP8 weight - collect for UnscaledFP8Linear replacement
                    if model_key.endswith('.weight'):
                        layer_key = model_key[:-7]  # Remove '.weight'
                        if layer_key not in fp8_layers:
                            fp8_layers[layer_key] = [None, None]
                        # Load directly to GPU as FP8 (no dtype conversion)
                        fp8_layers[layer_key][0] = tensor.to(self.device, copy=True)
                    elif model_key.endswith('.bias'):
                        layer_key = model_key[:-5]  # Remove '.bias'
                        if layer_key not in fp8_layers:
                            fp8_layers[layer_key] = [None, None]
                        # Load bias to GPU, convert from FP8
                        fp8_layers[layer_key][1] = tensor.to(device=self.device, dtype=self.dtype)
                else:
                    # Non-FP8 tensor - load directly to GPU
                    non_fp8_weights[model_key] = tensor.to(device=self.device, dtype=self.dtype)
        
        # Replace Linear layers with UnscaledFP8Linear first (before materializing)
        replaced = 0
        fp8_non_linear = {}  # FP8 tensors that aren't for Linear layers
        
        for layer_key, (weight, bias) in fp8_layers.items():
            if weight is None:
                continue
            
            try:
                # Navigate to parent module
                parts = layer_key.split('.')
                parent = self.transformer
                for part in parts[:-1]:
                    if part.isdigit():
                        parent = parent[int(part)]
                    else:
                        parent = getattr(parent, part)
                
                layer_name = parts[-1]
                old_layer = getattr(parent, layer_name, None)
                
                # Only replace if it's a Linear layer
                if old_layer is not None and isinstance(old_layer, nn.Linear):
                    # Create UnscaledFP8Linear (allocates only bias if present)
                    in_features = weight.shape[1]
                    out_features = weight.shape[0]
                    has_bias = bias is not None
                    
                    fp8_linear = UnscaledFP8Linear(
                        in_features, out_features,
                        bias=has_bias,
                        device=self.device,
                        compute_dtype=self.dtype,
                    )
                    fp8_linear.set_weight(weight, bias)
                    
                    # Replace the layer
                    setattr(parent, layer_name, fp8_linear)
                    replaced += 1
                else:
                    # Not a Linear layer - convert FP8 to compute dtype and load normally
                    fp8_non_linear[f"{layer_key}.weight"] = weight.to(dtype=self.dtype)
                    if bias is not None:
                        fp8_non_linear[f"{layer_key}.bias"] = bias
                
            except Exception as e:
                logger.debug(f"Could not replace {layer_key}: {e}")
                # Try to load as regular tensor
                fp8_non_linear[f"{layer_key}.weight"] = weight.to(dtype=self.dtype)
                if bias is not None:
                    fp8_non_linear[f"{layer_key}.bias"] = bias
        
        # Merge FP8 non-linear tensors into non_fp8_weights
        non_fp8_weights.update(fp8_non_linear)
        
        # Now load non-FP8 tensors directly to their locations
        loaded_other = 0
        for model_key, tensor in non_fp8_weights.items():
            try:
                set_module_tensor_to_device(
                    self.transformer, model_key, self.device, tensor
                )
                loaded_other += 1
            except Exception as e:
                logger.debug(f"Could not set {model_key}: {e}")
        
        logger.info(f"Loaded transformer: {replaced} FP8 Linear layers, {loaded_other} other tensors")
        
        # Initialize any remaining meta tensors (e.g., padding tokens not in checkpoint)
        self._materialize_meta_tensors()
        
        self.transformer.eval()
        
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def _materialize_meta_tensors(self) -> None:
        """
        Materialize any remaining meta tensors in the transformer.
        
        Some tensors like padding tokens are created in __init__ but not in checkpoint.
        These remain on meta device and need to be materialized with actual data.
        """
        for name, param in self.transformer.named_parameters():
            if param.device.type == 'meta':
                # Create actual tensor on target device with zeros
                new_param = nn.Parameter(
                    torch.zeros(param.shape, device=self.device, dtype=self.dtype),
                    requires_grad=False,
                )
                # Set the parameter
                parts = name.split('.')
                module = self.transformer
                for part in parts[:-1]:
                    if part.isdigit():
                        module = module[int(part)]
                    else:
                        module = getattr(module, part)
                setattr(module, parts[-1], new_param)
                logger.debug(f"Materialized meta parameter: {name}")
        
        for name, buffer in self.transformer.named_buffers():
            if buffer.device.type == 'meta':
                # Create actual tensor on target device with zeros
                new_buffer = torch.zeros(buffer.shape, device=self.device, dtype=self.dtype)
                # Set the buffer
                parts = name.split('.')
                module = self.transformer
                for part in parts[:-1]:
                    if part.isdigit():
                        module = module[int(part)]
                    else:
                        module = getattr(module, part)
                module.register_buffer(parts[-1], new_buffer)
                logger.debug(f"Materialized meta buffer: {name}")
    
    def _convert_checkpoint_key(self, key: str) -> Optional[str]:
        """
        Convert checkpoint key to model key.
        
        ComfyUI checkpoints may have different naming conventions.
        
        Args:
            key: Checkpoint key
            
        Returns:
            Model key or None if should skip
        """
        # Common prefixes to strip (order matters - compound prefixes first)
        prefixes = [
            'model.diffusion_model.',  # ComfyUI FP8 format
            'diffusion_model.',
            'model.',
            'transformer.',
        ]
        for prefix in prefixes:
            if key.startswith(prefix):
                key = key[len(prefix):]
                break
        
        # Skip scale weights (handled separately)
        if 'scale_weight' in key:
            return None
        
        return key
    
    def load_text_encoder(
        self,
        model_path: Optional[str] = None,
        tokenizer_path: Optional[str] = None,
        use_4bit: bool = False,
    ) -> None:
        """
        Load the text encoder.
        
        Args:
            model_path: Path to text encoder model
            tokenizer_path: Path to tokenizer (defaults to model_path)
            use_4bit: Enable 4-bit quantization for memory efficiency
        """
        path = model_path or self.text_encoder_path
        if path is None:
            raise ValueError("No text encoder path provided")
        
        # Use tokenizer_path if provided, else use sibling 'tokenizer' directory if exists
        tok_path = tokenizer_path
        if tok_path is None:
            sibling_tokenizer = os.path.join(os.path.dirname(path), "tokenizer")
            if os.path.isdir(sibling_tokenizer):
                tok_path = sibling_tokenizer
            else:
                tok_path = path  # Fall back to model path
        
        logger.info(f"Loading text encoder from {path}")
        
        # Override quantization if use_4bit is specified
        quantization = "4bit" if use_4bit else self.text_encoder_quantization

        # Constrain text encoder GPU budget to avoid 16GB spikes
        max_memory = None
        device_map = "auto"
        if torch.cuda.is_available():
            total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            # Leave ~8GB for transformer/activations, cap text encoder at remainder
            usable_gpu = max(total_vram_gb - 8.0, 2.0)
            max_memory = {0: f"{usable_gpu:.0f}GiB", "cpu": "32GiB"}

        self.text_encoder = ZImageTextEncoder(
            model_path=path,
            tokenizer_path=tok_path,
            device=self.device,
            dtype=self.dtype,
            quantization=quantization,
            device_map=device_map,
            max_memory=max_memory,
        )
        
        self.tokenizer = self.text_encoder.tokenizer
        
        self._loaded_components.append("text_encoder")
        logger.info("Text encoder loaded successfully")
    
    def load_vae(
        self,
        vae_path: Optional[str] = None,
    ) -> None:
        """
        Load the VAE decoder.
        
        Args:
            vae_path: Path to VAE model
        """
        path = vae_path or self.vae_path
        if path is None:
            raise ValueError("No VAE path provided")
        
        logger.info(f"Loading VAE from {path}")
        
        # Load VAE using diffusers' AutoencoderKL
        self.vae = AutoencoderKL.from_pretrained(
            path,
            torch_dtype=self.dtype,
        ).to(self.device)
        self.vae.eval()

        # Reduce VRAM during decode by tiling/slicing
        if hasattr(self.vae, "enable_slicing"):
            self.vae.enable_slicing()
        if hasattr(self.vae, "enable_tiling"):
            self.vae.enable_tiling()

        # Create an image processor for encode/decode convenience
        try:
            vae_scale_factor = 2 ** (len(self.vae.config.block_out_channels) - 1)
        except Exception:
            vae_scale_factor = 8
        self.image_processor = _NativeVaeImageProcessor(vae_scale_factor=vae_scale_factor)
        
        
        self._loaded_components.append("vae")
        logger.info("VAE loaded successfully")
    
    def setup_scheduler(
        self,
        num_inference_steps: int = 4,
        shift: float = 3.0,
    ) -> None:
        """
        Setup the flow matching scheduler.
        
        Args:
            num_inference_steps: Number of denoising steps
            shift: Sigma schedule shift (3.0 for Z-Image Turbo)
        """
        self.scheduler = FlowMatchEulerScheduler()
        self.scheduler.set_timesteps(num_inference_steps, device=self.device)
        logger.info(f"Scheduler setup with {num_inference_steps} steps (FlowMatchEulerScheduler)")
    
    def encode_prompt(
        self,
        prompt: Union[str, List[str]],
        negative_prompt: Optional[Union[str, List[str]]] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        Encode text prompt to embeddings.
        
        Args:
            prompt: Text prompt or list of prompts
            negative_prompt: Optional negative prompt
            
        Returns:
            Tuple of (prompt_embeds, negative_embeds, attention_mask)
        """
        if self.text_encoder is None:
            raise RuntimeError("Text encoder not loaded")
        
        # Encode positive prompt
        prompt_embeds, attention_mask = self.text_encoder.encode(
            prompt, return_attention_mask=True
        )
        
        # Encode negative prompt if provided
        negative_embeds = None
        if negative_prompt is not None:
            negative_embeds, _ = self.text_encoder.encode(
                negative_prompt, return_attention_mask=False
            )
        
        return prompt_embeds, negative_embeds, attention_mask
    
    @torch.no_grad()
    def generate(
        self,
        prompt: Union[str, List[str]],
        negative_prompt: Optional[Union[str, List[str]]] = None,
        height: int = 1024,
        width: int = 1024,
        num_inference_steps: int = 4,
        guidance_scale: float = 0.0,
        num_images_per_prompt: int = 1,
        generator: Optional[torch.Generator] = None,
        latents: Optional[torch.Tensor] = None,
        image: Optional[Any] = None,
        strength: float = 0.8,
        output_type: str = "pil",
        callback: Optional[Callable[[int, torch.Tensor], None]] = None,
        callback_steps: int = 1,
    ) -> Union[torch.Tensor, List["Image.Image"]]:
        """
        Generate images from text prompts.
        
        Args:
            prompt: Text prompt or list of prompts
            negative_prompt: Optional negative prompt
            height: Output image height
            width: Output image width
            num_inference_steps: Number of denoising steps
            guidance_scale: CFG scale (0 for Turbo models)
            num_images_per_prompt: Number of images per prompt
            generator: Random generator for reproducibility
            latents: Optional pre-generated latents
            output_type: Output type ("pil", "pt", "latent")
            callback: Optional callback(step, latents)
            callback_steps: Steps between callbacks
            
        Returns:
            Generated images (PIL or tensor depending on output_type)
        """
        # Validate components
        if self.transformer is None:
            raise RuntimeError("Transformer not loaded")
        if self.scheduler is None:
            self.setup_scheduler(num_inference_steps)
        is_img2img = image is not None
        if is_img2img and (strength < 0 or strength > 1):
            raise ValueError("Img2img strength must be between 0 and 1")
        
        # Handle batch
        if isinstance(prompt, str):
            prompt_batch_size = 1
            prompt = [prompt]
        else:
            prompt_batch_size = len(prompt)
        
        # Total batch size = prompts * images per prompt
        batch_size = prompt_batch_size * num_images_per_prompt
        
        # Encode prompts
        if self.text_encoder is not None:
            # Ensure text encoder is on GPU before encoding
            if hasattr(self.text_encoder, 'model') and self.text_encoder.model is not None:
                current_device = next(self.text_encoder.model.parameters()).device
                if current_device.type == 'cpu':
                    logger.debug("Moving text encoder back to GPU for encoding")
                    self.text_encoder.model.to(self.device)
            
            prompt_embeds, negative_embeds, attention_mask = self.encode_prompt(
                prompt, negative_prompt
            )
            # Repeat for num_images_per_prompt
            if num_images_per_prompt > 1:
                prompt_embeds = prompt_embeds.repeat(num_images_per_prompt, 1, 1)
                if negative_embeds is not None:
                    negative_embeds = negative_embeds.repeat(num_images_per_prompt, 1, 1)
                if attention_mask is not None:
                    attention_mask = attention_mask.repeat(num_images_per_prompt, 1)
            
            # Offload text encoder to CPU to free GPU memory for generation
            if hasattr(self.text_encoder, 'model') and self.text_encoder.model is not None:
                self.text_encoder.model.to('cpu')
                gc.collect()
                torch.cuda.empty_cache()
                logger.debug("Offloaded text encoder to CPU")
        else:
            # Dummy embeddings for testing
            prompt_embeds = torch.randn(
                batch_size, 77, 2560,
                device=self.device, dtype=self.dtype
            )
            negative_embeds = None
            attention_mask = None

        # Setup scheduler timesteps and handle img2img strength
        self.scheduler.set_timesteps(num_inference_steps, device=self.device)
        timesteps = self.scheduler.timesteps
        sigmas = self.scheduler.sigmas
        t_start = 0
        if is_img2img:
            init_timestep = min(int(num_inference_steps * strength), num_inference_steps)
            init_timestep = max(init_timestep, 1)
            t_start = max(num_inference_steps - init_timestep, 0)
            timesteps = timesteps[t_start:]
            sigmas = sigmas[t_start:]
            if timesteps.numel() == 0 or sigmas.numel() <= 1:
                raise ValueError("Strength setting removed all timesteps; choose lower strength or increase steps.")
        # Reset scheduler view to the truncated window and restart at step 0
        self.scheduler.timesteps = timesteps
        self.scheduler.sigmas = sigmas
        if hasattr(self.scheduler, "_step_index"):
            self.scheduler._step_index = 0
        self.scheduler.num_inference_steps = num_inference_steps
        num_inference_steps = timesteps.shape[0]

        def _randn(shape: Tuple[int, ...], dtype: torch.dtype = torch.float32) -> torch.Tensor:
            if generator is not None and self.device.type == "cuda":
                gen_device = getattr(generator, "device", torch.device("cpu"))
                if getattr(gen_device, "type", "cpu") == "cpu":
                    return torch.randn(
                        shape,
                        device="cpu",
                        dtype=dtype,
                        generator=generator,
                    ).to(self.device)
            return torch.randn(shape, device=self.device, dtype=dtype, generator=generator)

        # Setup latents
        latent_channels = ZIMAGE_CONFIG['in_channels']

        if is_img2img:
            if self.vae is None:
                raise RuntimeError("VAE must be loaded for img2img generation")

            if self.image_processor is None:
                try:
                    vae_scale_factor = 2 ** (len(self.vae.config.block_out_channels) - 1)
                except Exception:
                    vae_scale_factor = 8
                self.image_processor = _NativeVaeImageProcessor(vae_scale_factor=vae_scale_factor)

            # Derive target size from the input image when not provided
            if height is None or width is None:
                if hasattr(image, "height") and hasattr(image, "width"):
                    height = height or image.height
                    width = width or image.width
                elif isinstance(image, torch.Tensor):
                    height = height or int(image.shape[-2])
                    width = width or int(image.shape[-1])
            height = int(height)
            width = int(width)

            init_image = self.image_processor.preprocess(
                image,
                height=height,
                width=width,
            ).to(device=self.device, dtype=self.vae.dtype)

            image_latents = self.vae.encode(init_image).latent_dist.sample(generator)
            shift_factor = getattr(self.vae.config, "shift_factor", 0.0)
            scaling_factor = getattr(self.vae.config, "scaling_factor", 1.0)
            image_latents = (image_latents - shift_factor) * scaling_factor

            if batch_size > image_latents.shape[0]:
                if batch_size % image_latents.shape[0] != 0:
                    raise ValueError(
                        f"Cannot duplicate image latents of batch size {image_latents.shape[0]} to {batch_size}"
                    )
                repeat_count = batch_size // image_latents.shape[0]
                image_latents = torch.cat([image_latents] * repeat_count, dim=0)
            else:
                image_latents = image_latents[:batch_size]

            image_latents = image_latents.to(device=self.device, dtype=torch.float32)

            if latents is None:
                noise = _randn(tuple(image_latents.shape), dtype=torch.float32)
                # Mirror diffusers img2img init: blend by normalized timestep fraction
                timestep_value = float(timesteps[0].item()) if timesteps.numel() > 0 else 0.0
                timestep_ratio = timestep_value / max(self.scheduler.config.num_train_timesteps, 1)
                logger.info(f"[IMG2IMG] strength={strength}, t_start={t_start}, first_timestep={timestep_value}, timestep_ratio={timestep_ratio:.4f}")
                logger.info(f"[IMG2IMG] image_latents std={image_latents.std().item():.4f}, noise std={noise.std().item():.4f}")
                latents = (1.0 - timestep_ratio) * image_latents + timestep_ratio * noise
                logger.info(f"[IMG2IMG] blended latents std={latents.std().item():.4f} (image_weight={1.0-timestep_ratio:.4f}, noise_weight={timestep_ratio:.4f})")
            else:
                latents = latents.to(device=self.device, dtype=torch.float32)
        else:
            latent_height = height // 8
            latent_width = width // 8
            if latents is None:
                latents = _randn(
                    (batch_size, latent_channels, latent_height, latent_width),
                    dtype=self.dtype,
                )
            else:
                latents = latents.to(device=self.device, dtype=self.dtype)

            if hasattr(self.scheduler, 'init_noise_sigma'):
                latents = latents * self.scheduler.init_noise_sigma
        
        # Denoising loop
        num_tokens = prompt_embeds.shape[1] if prompt_embeds is not None else 77
        
        # Determine if CFG should be used
        # CFG is applied when guidance_scale > 1.0 and we have negative embeddings
        use_cfg = guidance_scale > 1.0 and negative_embeds is not None

        for i, t in enumerate(timesteps):
            # Expand timestep and normalize to [0, 1] like diffusers pipeline
            timestep = t.expand(batch_size)
            timestep = (self.scheduler.num_train_timesteps - timestep) / max(self.scheduler.num_train_timesteps, 1)
            
            # Prepare conditioning
            if use_cfg:
                # CFG: concat negative and positive
                latent_model_input = torch.cat([latents, latents], dim=0)
                prompt_embeds_input = torch.cat([negative_embeds, prompt_embeds], dim=0)
                timestep_input = timestep.repeat(2)
            else:
                latent_model_input = latents
                prompt_embeds_input = prompt_embeds
                timestep_input = timestep
            
            # Model prediction
            noise_pred = self.transformer(
                latent_model_input,
                timestep_input,
                prompt_embeds_input,
                num_tokens=num_tokens,
                attention_mask=attention_mask,
            )
            
            # CRITICAL: Negate the model output (official Z-Image does this!)
            # Official code: noise_pred = -noise_pred.squeeze(2)
            noise_pred = -noise_pred
            
            # Debug logging for all steps
            logger.info(f"[DEBUG] Step {i}: t={t.item():.2f}, latents std={latents.std().item():.4f}, noise_pred std={noise_pred.std().item():.4f}")
            
            # Apply CFG
            if use_cfg:
                noise_pred_neg, noise_pred_pos = noise_pred.chunk(2)
                noise_pred = noise_pred_neg + guidance_scale * (noise_pred_pos - noise_pred_neg)
            
            # Convert to float32 for scheduler step (official does this)
            noise_pred = noise_pred.to(torch.float32)
            latents = latents.to(torch.float32)
            
            # Scheduler step - extract prev_sample from output
            scheduler_output = self.scheduler.step(noise_pred, t, latents)
            latents = scheduler_output.prev_sample if hasattr(scheduler_output, "prev_sample") else scheduler_output
            
            # Debug: check latents after scheduler step
            logger.info(f"[DEBUG] Step {i} after: latents std={latents.std().item():.4f}")
            
            # Callback
            if callback is not None and (i + 1) % callback_steps == 0:
                try:
                    callback(self, i, t, {"latents": latents})
                except TypeError:
                    # Fallback for simpler callbacks that expect only step
                    callback(i)
        
        # Return latents if requested
        if output_type == "latent":
            return latents
        
        # Decode latents on GPU
        if self.vae is not None:
            # Scale latents for VAE
            latents = latents / self.vae.config.scaling_factor
            latents = latents.to(dtype=self.vae.dtype, device=self.device)
            
            # Ensure VAE is on GPU
            self.vae.to(self.device)
            
            images = self.vae.decode(latents).sample
            images = (images / 2 + 0.5).clamp(0, 1)
        else:
            # Return raw latents if no VAE
            images = latents
        
        # Convert to PIL if requested
        if output_type == "pil":
            
            # Convert to numpy: (B, C, H, W) -> (B, H, W, C)
            images_np = images.permute(0, 2, 3, 1).cpu().float().numpy()
            images_np = (images_np * 255).clip(0, 255).astype(np.uint8)
            
            pil_images = [Image.fromarray(img) for img in images_np]
            return pil_images
        
        return images
    
    def unload(self, components: Optional[List[str]] = None) -> None:
        """
        Unload components to free memory.
        
        Args:
            components: List of components to unload, or None for all
        """
        if components is None:
            components = ["transformer", "text_encoder", "vae"]
        
        if "transformer" in components and self.transformer is not None:
            del self.transformer
            self.transformer = None
            if "transformer" in self._loaded_components:
                self._loaded_components.remove("transformer")
        
        if "text_encoder" in components and self.text_encoder is not None:
            self.text_encoder.unload()
            self.text_encoder = None
            self.tokenizer = None
            if "text_encoder" in self._loaded_components:
                self._loaded_components.remove("text_encoder")
        
        if "vae" in components and self.vae is not None:
            del self.vae
            self.vae = None
            if "vae" in self._loaded_components:
                self._loaded_components.remove("vae")
        
        # Force garbage collection
        gc.collect()
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except (RuntimeError, AttributeError):
            # torch may be None during interpreter shutdown
            pass
        
        logger.info(f"Unloaded components: {components}")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.unload()
        except (RuntimeError, TypeError, AttributeError):
            # Ignore errors during interpreter shutdown
            pass
