"""
Native Z-Image Pipeline.

This module provides a complete image generation pipeline for Z-Image
without diffusers dependency, supporting FP8 scaled checkpoints.
"""

from __future__ import annotations

import gc
import numpy as np
from PIL import Image
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from safetensors import safe_open
from safetensors.torch import load_file as load_safetensors

from airunner_services.art.managers.zimage.native.fp8_ops import (
    FP8Linear,
    UnscaledFP8Linear,
    QuantizedTensor,
    TensorCoreFP8Layout,
    is_fp8_scaled_checkpoint,
)
from airunner_services.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)
from airunner_services.art.managers.zimage.native.nextdit_model import (
    NextDiT,
    ZIMAGE_CONFIG,
    create_zimage_transformer,
)
from airunner_services.art.managers.zimage.native.zimage_text_encoder import (
    ZImageTextEncoder,
    ZImageTokenizer,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_prompt_helper import (
    ZImageNativePipelinePromptHelper,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_generation_helper import (
    ZImageNativePipelineGenerationHelper,
)
from airunner_services.art.runtime_memory import clear_memory
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

    def _get_prompt_helper(self) -> ZImageNativePipelinePromptHelper:
        """Return the cached prompt-conditioning helper."""
        helper = getattr(self, "_prompt_helper", None)
        if helper is None:
            helper = ZImageNativePipelinePromptHelper(self)
            self._prompt_helper = helper
        return helper

    def _get_generation_helper(self) -> ZImageNativePipelineGenerationHelper:
        """Return the cached generation helper."""
        helper = getattr(self, "_generation_helper", None)
        if helper is None:
            helper = ZImageNativePipelineGenerationHelper(self)
            self._generation_helper = helper
        return helper

    def _ensure_image_processor(self) -> None:
        """Create the lightweight VAE image processor on first use."""
        if self.image_processor is not None:
            return
        try:
            vae_scale_factor = 2 ** (len(self.vae.config.block_out_channels) - 1)
        except Exception:
            vae_scale_factor = 8
        self.image_processor = _NativeVaeImageProcessor(
            vae_scale_factor=vae_scale_factor
        )

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
        materialized_params = 0
        materialized_buffers = 0

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
                materialized_params += 1
        
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
                materialized_buffers += 1

        if materialized_params or materialized_buffers:
            logger.debug(
                "Materialized %d meta parameters and %d meta buffers",
                materialized_params,
                materialized_buffers,
            )
    
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
        """Load the text encoder."""
        self._get_prompt_helper().load_text_encoder(
            model_path,
            tokenizer_path,
            use_4bit,
        )

    def _build_text_encoder_load_plan(
        self,
        quantization: Optional[str],
    ) -> Dict[str, Any]:
        """Choose a text-encoder loading strategy for current free VRAM."""
        return self._get_prompt_helper().build_text_encoder_load_plan(
            quantization
        )

    def _ensure_text_encoder_ready(self) -> None:
        """Load text encoder weights on demand before prompt encoding."""
        self._get_prompt_helper().ensure_text_encoder_ready()

    def _prepare_text_encoder_for_encoding(self) -> None:
        """Move fully GPU-resident encoders back to the active device."""
        self._get_prompt_helper().prepare_text_encoder_for_encoding()

    def _ensure_vae_on_device(self) -> None:
        """Move the VAE to the active device before encode/decode."""
        if self.vae is None:
            raise RuntimeError("VAE not loaded")
        vae_device = next(self.vae.parameters()).device
        if vae_device != self.device:
            logger.debug(f"Moving VAE from {vae_device} to {self.device}")
            self.vae.to(self.device)

    def _release_text_encoder_after_encoding(self) -> None:
        """Free text-encoder GPU memory once prompt embeddings are ready."""
        self._get_prompt_helper().release_text_encoder_after_encoding()

    def _move_prompt_conditioning_to_device(
        self,
        prompt_embeds: torch.Tensor,
        negative_embeds: Optional[torch.Tensor],
        attention_mask: Optional[torch.Tensor],
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """Move prompt-conditioning tensors to the transformer device."""
        return self._get_prompt_helper().move_prompt_conditioning_to_device(
            prompt_embeds,
            negative_embeds,
            attention_mask,
        )
    
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
        vae_device = self.device
        if self.device.type == "cuda":
            vae_device = torch.device("cpu")
            logger.info(
                "Loading VAE on CPU; it will move to GPU on first use"
            )
        
        # Load VAE using diffusers' AutoencoderKL
        self.vae = AutoencoderKL.from_pretrained(
            path,
            torch_dtype=self.dtype,
        ).to(vae_device)
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
        """Encode text prompt to embeddings."""
        return self._get_prompt_helper().encode_prompt(
            prompt,
            negative_prompt,
        )
    
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
        """Generate images from text prompts."""
        return self._get_generation_helper().generate(
            prompt,
            negative_prompt,
            height,
            width,
            num_inference_steps,
            guidance_scale,
            num_images_per_prompt,
            generator,
            latents,
            image,
            strength,
            output_type,
            callback,
            callback_steps,
        )
    
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
        
        clear_memory(self.device)
        
        logger.info(f"Unloaded components: {components}")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.unload()
        except (RuntimeError, TypeError, AttributeError):
            # Ignore errors during interpreter shutdown
            pass
