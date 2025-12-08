"""Z-Image pipeline loading mixin."""

import gc
import os
from pathlib import Path
from typing import Any, Dict, Optional

import torch
from safetensors import safe_open

from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.enums import SignalCode
from airunner.components.art.utils.model_file_checker import ModelFileChecker


def _clear_gpu_memory() -> None:
    """Aggressively clear GPU memory."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    gc.collect()


class ZImagePipelineLoadingMixin:
    """Mixin for Z-Image pipeline loading operations.
    
    Overrides the base _set_pipe method to handle Z-Image's specific
    requirements for loading from single-file checkpoints, particularly
    the need to load the text encoder separately.
    """

    def _set_pipe(self, config_path: str, data: Dict):
        """Load Z-Image pipeline from model file.
        
        Overrides base class method to handle Z-Image specific loading.
        Z-Image single-file checkpoints don't include the text encoder,
        so we need to load it separately from HuggingFace.

        Args:
            config_path: Path to pipeline configuration directory (unused for Z-Image).
            data: Dictionary of pipeline initialization parameters.
        """
        from airunner.components.art.pipelines.z_image import ZImagePipeline
        
        pipeline_class = self._pipeline_class
        if pipeline_class is None:
            pipeline_class = ZImagePipeline
            
        self.logger.info(f"Loading {pipeline_class.__name__} from {self.model_path}")
        
        # Check for missing files and trigger download if needed
        self._ensure_zimage_files_available()
        
        _clear_gpu_memory()
        
        # Determine if we have a complete pretrained directory structure
        model_path = Path(self.model_path)
        is_single_file = model_path.is_file()
        
        if is_single_file:
            model_dir = model_path.parent
        else:
            model_dir = model_path
        
        has_pretrained_structure = self._has_complete_pretrained_structure(model_dir)

        # IMPORTANT: If user selected a specific checkpoint file, ALWAYS use single-file loading
        # even if a pretrained directory structure exists. This ensures FP8/quantized checkpoints
        # are loaded correctly instead of being ignored in favor of full-precision pretrained weights.
        #
        # FP8 scaled checkpoints (e.g., fp8_e4m3fn) use our native implementation for efficient
        # loading without the full 32GB+ memory spike of diffusers. Detect both by name and by
        # sampling the safetensors contents to avoid misclassification.
        is_fp8_checkpoint = self._detect_fp8_checkpoint(model_path)
        
        if is_single_file and is_fp8_checkpoint:
            self.logger.info(
                f"FP8 scaled checkpoint detected ({model_path.name}). "
                f"Using native FP8 pipeline for memory-efficient loading."
            )
            self._load_native_fp8_pipeline(str(model_path), str(model_dir), pipeline_class, data)
        elif is_single_file and self.use_from_single_file:
            self.logger.info(
                f"Loading from single-file checkpoint: {model_path.name}"
            )
            self._load_from_single_file(self.model_path, pipeline_class, data, is_fp8_checkpoint=is_fp8_checkpoint)
        elif has_pretrained_structure and not is_single_file:
            self.logger.info(
                "Complete pretrained structure found - loading from pretrained directory"
            )
            self._load_from_pretrained(str(model_dir), pipeline_class, data)
        elif self.use_from_single_file:
            self._load_from_single_file(self.model_path, pipeline_class, data)
        else:
            self._load_from_pretrained(self.model_path, pipeline_class, data)
        
        # Debug: verify _pipe was set
        self.logger.info(f"[ZIMAGE DEBUG] After _set_pipe: self._pipe={self._pipe}, self={id(self)}")

        # Load LoRA adapters if available for this pipeline
        try:
            if hasattr(self, "_load_lora") and self._pipe is not None:
                self.logger.info("[ZIMAGE] Loading LoRA adapters")
                self._load_lora()
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.warning(f"[ZIMAGE] Failed to load LoRA adapters: {exc}")
        
        _clear_gpu_memory()

    def _has_complete_pretrained_structure(self, model_dir: Path) -> bool:
        """Check if the model directory has all required pretrained components.
        
        Args:
            model_dir: Path to the model directory.
            
        Returns:
            True if all required component folders exist with config files.
        """
        required_components = ["transformer", "text_encoder", "vae", "scheduler", "tokenizer"]
        
        for component in required_components:
            component_path = model_dir / component
            if not component_path.is_dir():
                self.logger.debug(f"Missing component directory: {component}")
                return False
            
            # Check for config file - different components use different names
            if component == "tokenizer":
                config_file = component_path / "tokenizer_config.json"
            elif component == "scheduler":
                config_file = component_path / "scheduler_config.json"
            else:
                config_file = component_path / "config.json"
                
            if not config_file.exists():
                self.logger.debug(f"Missing config file: {config_file}")
                return False
        
        # Check for model_index.json (indicates full pretrained structure)
        model_index = model_dir / "model_index.json"
        if not model_index.exists():
            self.logger.debug("Missing model_index.json")
            return False
            
        return True

    def _detect_fp8_checkpoint(self, model_path: Path) -> bool:
        """Detect whether the safetensors checkpoint stores FP8 weights.

        We cannot rely solely on filename markers; inspect a small sample of
        tensors to see if any are stored in float8 or use scale_weight keys.

        Args:
            model_path: Path to the checkpoint file.

        Returns:
            True if FP8 tensors are detected, otherwise False.
        """
        name_hint = "fp8" in model_path.name.lower() or any(
            marker in model_path.name.lower() for marker in ("e4m3", "e5m2")
        )

        if not model_path.is_file() or model_path.suffix != ".safetensors":
            return name_hint

        try:
            with safe_open(model_path, framework="pt") as f:
                has_scale = False
                for i, key in enumerate(f.keys()):
                    if "scale_weight" in key:
                        has_scale = True
                    tensor = f.get_tensor(key)
                    if tensor.dtype in (
                        torch.float8_e4m3fn,
                        torch.float8_e5m2,
                        getattr(torch, "float8_e4m3fnuz", None),
                        getattr(torch, "float8_e5m2fnuz", None),
                    ):
                        return True
                    if i >= 32:  # sample a small subset to avoid CPU blowups
                        break
                return name_hint or has_scale
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug(f"FP8 detection failed for {model_path}: {exc}")
            return name_hint

    def _ensure_zimage_files_available(self) -> None:
        """Ensure Z-Image model files exist locally, otherwise trigger download.
        
        Checks for missing companion files (text_encoder, tokenizer, vae, scheduler)
        and triggers a download if any are missing or incomplete.
        """
        # Get the model directory (parent of single file, or the dir itself)
        model_path = Path(self.model_path)
        if model_path.is_file():
            model_dir = model_path.parent
        else:
            model_dir = model_path
        
        should_download, download_info = ModelFileChecker.should_trigger_download(
            model_path=str(model_dir),
            model_type="art",
            version="Z-Image Turbo",
            pipeline_action="txt2img",
        )
        
        if not should_download:
            self.logger.info("All Z-Image model files present")
            return
        
        repo_id = download_info.get("repo_id")
        missing_files = download_info.get("missing_files", [])
        
        self.logger.info(
            f"Missing {len(missing_files)} Z-Image model files, triggering download from {repo_id}"
        )
        self.logger.debug(f"Missing files: {missing_files}")
        
        self.emit_signal(
            SignalCode.ART_MODEL_DOWNLOAD_REQUIRED,
            {
                "repo_id": repo_id,
                "model_path": str(model_dir),
                "missing_files": missing_files,
                "version": "Z-Image Turbo",
                "pipeline_action": "txt2img",
            },
        )
        raise RuntimeError(
            f"Z-Image model files missing from {model_dir}, download triggered"
        )

    def _load_from_pretrained(self, model_path: str, pipeline_class: Any, data: Dict):
        """Load Z-Image from HuggingFace pretrained directory.
        
        Since ZImageTransformer2DModel isn't in diffusers yet, we need to manually
        load each component and assemble the pipeline.
        
        Quantization depends on user's precision setting:
        - 4bit: Uses NF4 quantization (~75% memory reduction)
        - 8bit: Uses 8-bit quantization (~50% memory reduction)  
        - Otherwise: No quantization, uses selected dtype (bfloat16/float16/float32)
        """
        self.logger.info(f"Loading Z-Image from pretrained: {model_path}")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from transformers import BitsAndBytesConfig as TransformersBnBConfig
            from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler
            from diffusers import BitsAndBytesConfig as DiffusersBnBConfig
            from airunner.components.art.pipelines.z_image import ZImageTransformer2DModel
        except ImportError as e:
            self.logger.error(f"Missing required imports: {e}")
            raise
        
        model_dir = Path(model_path)
        
        # Check user's precision/quantization setting
        use_quant = getattr(self, 'use_quantization', False)
        quant_bits = getattr(self, 'quantization_bits', None)
        model_dtype = self.data_type
        
        # Check if we're falling back from FP8 - force 4-bit quantization
        force_quant_for_fp8 = getattr(self, '_force_quantization_for_fp8_fallback', False)
        if force_quant_for_fp8:
            self.logger.info("FP8 fallback mode - forcing 4-bit quantization for transformer and text encoder")
            use_quant = True
            quant_bits = 4
            # Clear the flag
            self._force_quantization_for_fp8_fallback = False
        
        self.logger.info(f"Precision settings - use_quantization: {use_quant}, bits: {quant_bits}, dtype: {model_dtype}")
        
        # Calculate max memory for device_map="auto" to leave room for VAE decode
        # We need ~2-3GB free for VAE decode + activations
        max_memory_for_models = None
        if torch.cuda.is_available() and use_quant:
            total_vram_bytes = torch.cuda.get_device_properties(0).total_memory
            total_vram_gb = total_vram_bytes / (1024**3)
            # Reserve 3GB for VAE decode and other operations
            reserved_gb = 3.0
            usable_vram_gb = max(total_vram_gb - reserved_gb, 4.0)  # At least 4GB for models
            max_memory_for_models = {0: f"{usable_vram_gb:.0f}GiB", "cpu": "32GiB"}
            self.logger.info(f"VRAM budget: {usable_vram_gb:.1f}GB for models (reserving {reserved_gb}GB for VAE/activations)")
        
        # Configure quantization if enabled
        transformer_bnb_config = None
        text_encoder_bnb_config = None
        
        if use_quant and quant_bits == 4:
            # 4-bit NF4 quantization for maximum memory savings
            self.logger.info("Using 4-bit NF4 quantization")
            transformer_bnb_config = DiffusersBnBConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            text_encoder_bnb_config = TransformersBnBConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif use_quant and quant_bits == 8:
            # 8-bit quantization
            self.logger.info("Using 8-bit quantization")
            transformer_bnb_config = DiffusersBnBConfig(
                load_in_8bit=True,
            )
            text_encoder_bnb_config = TransformersBnBConfig(
                load_in_8bit=True,
            )
        else:
            self.logger.info(f"No quantization - using dtype: {model_dtype}")
        
        # Load transformer
        transformer_path = model_dir / "transformer"
        quant_info = f"({quant_bits}-bit quantized)" if use_quant else f"(dtype: {model_dtype})"
        self.logger.info(f"Loading transformer from {transformer_path} {quant_info}")
        try:
            load_kwargs = {
                "torch_dtype": model_dtype,
                "local_files_only": True,
            }
            if transformer_bnb_config is not None:
                load_kwargs["quantization_config"] = transformer_bnb_config
                # Use device_map and max_memory for consistent VRAM management
                load_kwargs["device_map"] = "auto"
                if max_memory_for_models is not None:
                    load_kwargs["max_memory"] = max_memory_for_models
            transformer = ZImageTransformer2DModel.from_pretrained(
                str(transformer_path),
                **load_kwargs,
            )
        except Exception as e:
            self.logger.error(f"Failed to load transformer: {e}")
            raise
        
        # Load text encoder
        text_encoder_path = model_dir / "text_encoder"
        tokenizer_path = model_dir / "tokenizer"
        self.logger.info(f"Loading text encoder from {text_encoder_path} {quant_info}")
        try:
            load_kwargs = {
                "local_files_only": True,
            }
            if text_encoder_bnb_config is not None:
                load_kwargs["quantization_config"] = text_encoder_bnb_config
                load_kwargs["device_map"] = "auto"
                # Apply max_memory to prevent accelerate from using all VRAM
                if max_memory_for_models is not None:
                    load_kwargs["max_memory"] = max_memory_for_models
            else:
                load_kwargs["torch_dtype"] = model_dtype
            text_encoder = AutoModelForCausalLM.from_pretrained(
                str(text_encoder_path),
                **load_kwargs,
            )
            tokenizer = AutoTokenizer.from_pretrained(
                str(tokenizer_path),
                local_files_only=True,
            )
        except Exception as e:
            self.logger.error(f"Failed to load text encoder: {e}")
            raise
        
        # Load VAE (small, no quantization needed - ~160MB)
        vae_path = model_dir / "vae"
        self.logger.info(f"Loading VAE from {vae_path}")
        try:
            vae = AutoencoderKL.from_pretrained(
                str(vae_path),
                torch_dtype=model_dtype,
                local_files_only=True,
            )
        except Exception as e:
            self.logger.error(f"Failed to load VAE: {e}")
            raise
        
        # Load scheduler with appropriate configuration based on user selection
        scheduler = self._load_zimage_scheduler(model_dir / "scheduler")
        
        # Assemble the pipeline
        self.logger.info("Assembling ZImagePipeline from components...")
        try:
            self._pipe = pipeline_class(
                transformer=transformer,
                vae=vae,
                text_encoder=text_encoder,
                tokenizer=tokenizer,
                scheduler=scheduler,
            )
            precision_info = f"{quant_bits}-bit quantized" if use_quant else f"dtype: {model_dtype}"
            self.logger.info(f"Pipeline assembled successfully ({precision_info})")
        except Exception as e:
            self.logger.error(f"Failed to assemble pipeline: {e}")
            raise

    def _load_from_single_file(
        self,
        model_path: str,
        pipeline_class: Any,
        data: Dict,
        *,
        is_fp8_checkpoint: Optional[bool] = None,
    ):
        """Load Z-Image from single safetensors file (e.g., from CivitAI).
        
        For single-file loading, the text encoder, VAE, scheduler, and tokenizer
        are loaded from the companion folders in the same directory as the 
        checkpoint file.
        
        Respects user's precision/quantization settings.
        
        CRITICAL: FP8 pre-quantized checkpoints (like zImageTurboQuantized_fp8*.safetensors)
        contain transformer weights that are already quantized. We should NOT apply
        additional bitsandbytes quantization to the transformer, only to the text encoder.
        """
        self.logger.info(f"Loading Z-Image from single file: {model_path}")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from transformers import BitsAndBytesConfig as TransformersBnBConfig
            from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler
            from airunner.components.art.pipelines.z_image import ZImageTransformer2DModel
        except ImportError as e:
            self.logger.error(f"Missing required imports: {e}")
            raise
        
        # Check user's precision/quantization setting
        use_quant = getattr(self, 'use_quantization', False)
        quant_bits = getattr(self, 'quantization_bits', None)
        model_dtype = self.data_type
        
        # Detect if this is a pre-quantized FP8 checkpoint
        if is_fp8_checkpoint is None:
            model_filename = os.path.basename(model_path).lower()
            is_fp8_checkpoint = "fp8" in model_filename or "e4m3" in model_filename or "e5m2" in model_filename
            if not is_fp8_checkpoint:
                is_fp8_checkpoint = self._detect_fp8_checkpoint(Path(model_path))
        
        if is_fp8_checkpoint:
            self.logger.info(
                f"Detected FP8 pre-quantized checkpoint - transformer is already quantized"
            )
        
        self.logger.info(f"Precision settings - use_quantization: {use_quant}, bits: {quant_bits}, dtype: {model_dtype}")
        
        # Get the directory containing the checkpoint - companion folders
        # (text_encoder, tokenizer, vae, scheduler) are in the same directory
        model_dir = os.path.dirname(model_path)
        self.logger.info(f"Loading companion files from: {model_dir}")
        
        # Calculate max memory for device_map to prevent all weights going to CPU
        max_memory_for_text_encoder = None
        if torch.cuda.is_available():
            total_vram_bytes = torch.cuda.get_device_properties(0).total_memory
            total_vram_gb = total_vram_bytes / (1024**3)
            # For FP8 checkpoints: transformer is ~6GB, reserve 4GB for generation overhead
            # For text encoder with 4-bit quant: ~2.4GB on GPU, rest can be on CPU
            if is_fp8_checkpoint:
                # Reserve more GPU memory for the FP8 transformer
                text_encoder_vram_budget = max(total_vram_gb - 10.0, 2.0)
            else:
                # Non-FP8: more budget for text encoder
                text_encoder_vram_budget = max(total_vram_gb - 6.0, 2.0)
            max_memory_for_text_encoder = {
                0: f"{text_encoder_vram_budget:.0f}GiB",
                "cpu": "24GiB"  # Limit CPU RAM usage
            }
            self.logger.info(
                f"Text encoder VRAM budget: {text_encoder_vram_budget:.1f}GB (total VRAM: {total_vram_gb:.1f}GB)"
            )
        
        # Configure text encoder quantization if enabled
        # ALWAYS quantize text encoder for FP8 checkpoints to save memory
        text_encoder_bnb_config = None
        if use_quant and quant_bits == 4:
            text_encoder_bnb_config = TransformersBnBConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif use_quant and quant_bits == 8:
            text_encoder_bnb_config = TransformersBnBConfig(
                load_in_8bit=True,
            )
        elif is_fp8_checkpoint:
            # For FP8 checkpoints, default to 4-bit text encoder to save memory
            self.logger.info(
                "FP8 checkpoint detected - using 4-bit quantization for text encoder to save memory"
            )
            text_encoder_bnb_config = TransformersBnBConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        
        # Load the text encoder from the local text_encoder subfolder
        text_encoder_path = os.path.join(model_dir, "text_encoder")
        tokenizer_path = os.path.join(model_dir, "tokenizer")
        
        quant_info = "(4-bit quantized)" if text_encoder_bnb_config else f"(dtype: {model_dtype})"
        self.logger.info(f"Loading text encoder from {text_encoder_path} {quant_info}")
        try:
            load_kwargs = {
                "local_files_only": True,
            }
            if text_encoder_bnb_config is not None:
                load_kwargs["quantization_config"] = text_encoder_bnb_config
                load_kwargs["device_map"] = "auto"
                if max_memory_for_text_encoder is not None:
                    load_kwargs["max_memory"] = max_memory_for_text_encoder
            else:
                load_kwargs["torch_dtype"] = model_dtype
            text_encoder = AutoModelForCausalLM.from_pretrained(
                text_encoder_path,
                **load_kwargs,
            )
            tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_path,
                local_files_only=True,
            )
        except Exception as e:
            self.logger.error(f"Failed to load text encoder: {e}")
            raise
        
        # Now load the pipeline with the text encoder pre-loaded
        pipe_kwargs = {
            "torch_dtype": model_dtype,
            "text_encoder": text_encoder,
            "tokenizer": tokenizer,
            **data,
        }
        
        # Get config path if available
        config_path = self._get_config_path()
        if config_path and os.path.isdir(str(config_path)):
            pipe_kwargs["config"] = config_path
        
        try:
            self._pipe = pipeline_class.from_single_file(
                model_path,
                **pipe_kwargs
            )
            self.logger.info(f"Pipeline loaded from single file {quant_info}")
        except Exception as e:
            self.logger.error(f"Failed to load from single file: {e}")
            # Prefer native FP8 loader on failure to avoid CPU-only fallback
            if is_fp8_checkpoint:
                self.logger.info("Retrying with native FP8 pipeline after from_single_file failure")
                self._load_native_fp8_pipeline(model_path, model_dir, pipeline_class, data)
                return
            # Fall back to manual assembly
            self._load_single_file_with_fallback(
                model_path, pipeline_class, text_encoder, tokenizer, data
            )

    def _load_single_file_with_fallback(
        self, 
        model_path: str, 
        pipeline_class: Any,
        text_encoder: Any,
        tokenizer: Any,
        data: Dict,
    ):
        """Fallback loading: Manually assemble pipeline from components.
        
        This is used when from_single_file fails (which is expected since
        ZImageTransformer2DModel is not in diffusers' FromOriginalModelMixin whitelist).
        
        We load the transformer weights directly from the safetensors file and
        load them into a ZImageTransformer2DModel instance.
        """
        self.logger.info("Attempting fallback: manual component assembly...")
        
        try:
            from safetensors.torch import load_file as load_safetensors
            from transformers import AutoModelForCausalLM, AutoTokenizer as HFAutoTokenizer
            from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler
            from airunner.components.art.pipelines.z_image import ZImageTransformer2DModel
            
            # Get user's precision setting
            model_dtype = self.data_type
            
            # Get the directory containing the checkpoint
            model_dir = os.path.dirname(model_path)
            
            # Load the transformer config from the companion folder
            transformer_config_path = os.path.join(model_dir, "transformer", "config.json")
            
            if os.path.exists(transformer_config_path):
                self.logger.info(f"Loading transformer config from {transformer_config_path}")
                # Create model from config
                transformer = ZImageTransformer2DModel.from_config(transformer_config_path)
            else:
                self.logger.info("No transformer config found, using default Z-Image config")
                # Use default Z-Image Turbo config
                transformer = ZImageTransformer2DModel(
                    all_patch_size=(2,),
                    all_f_patch_size=(1,),
                    in_channels=16,
                    dim=3840,
                    n_layers=30,
                    n_refiner_layers=2,
                    n_heads=30,
                    n_kv_heads=30,
                    norm_eps=1e-5,
                    qk_norm=True,
                    cap_feat_dim=2560,
                    rope_theta=256.0,
                    t_scale=1000.0,
                    axes_dims=[32, 48, 48],
                    axes_lens=[1024, 512, 512],
                )
            
            # Load weights from the safetensors checkpoint
            self.logger.info(f"Loading transformer weights from {model_path}")
            state_dict = load_safetensors(model_path)
            
            # Filter to only transformer keys (exclude VAE, etc. if present)
            # Z-Image checkpoints typically have transformer keys without prefix
            transformer_keys = [k for k in state_dict.keys() if not k.startswith(('vae.', 'text_encoder.'))]
            if transformer_keys:
                transformer_state_dict = {k: v for k, v in state_dict.items() if k in transformer_keys}
            else:
                transformer_state_dict = state_dict
            
            # Load the state dict - use strict=False to handle any key mismatches
            missing, unexpected = transformer.load_state_dict(transformer_state_dict, strict=False)
            if missing:
                self.logger.warning(f"Missing keys when loading transformer: {len(missing)} keys")
                self.logger.debug(f"Missing keys: {missing[:10]}...")  # Log first 10
            if unexpected:
                self.logger.warning(f"Unexpected keys when loading transformer: {len(unexpected)} keys")
                self.logger.debug(f"Unexpected keys: {unexpected[:10]}...")
            
            # Move to correct dtype
            transformer = transformer.to(model_dtype)
            self.logger.info(f"Transformer loaded successfully (dtype: {model_dtype})")
            
            # Load VAE from local vae subfolder
            vae_path = os.path.join(model_dir, "vae")
            self.logger.info(f"Loading VAE from {vae_path}")
            vae = AutoencoderKL.from_pretrained(
                vae_path,
                torch_dtype=model_dtype,
                local_files_only=True,
            )
            
            # Load scheduler using the helper method
            scheduler_path = os.path.join(model_dir, "scheduler")
            self.logger.info(f"Loading scheduler from {scheduler_path}")
            scheduler = self._load_zimage_scheduler(Path(scheduler_path))
            
            # If text encoder wasn't provided, load it from local path
            if text_encoder is None or tokenizer is None:
                text_encoder_path = os.path.join(model_dir, "text_encoder")
                tokenizer_path = os.path.join(model_dir, "tokenizer")
                self.logger.info(f"Loading text encoder from {text_encoder_path}")
                text_encoder = AutoModelForCausalLM.from_pretrained(
                    text_encoder_path,
                    torch_dtype=model_dtype,
                    local_files_only=True,
                )
                tokenizer = HFAutoTokenizer.from_pretrained(
                    tokenizer_path,
                    local_files_only=True,
                )
            
            # Assemble the pipeline
            self._pipe = pipeline_class(
                transformer=transformer,
                vae=vae,
                text_encoder=text_encoder,
                tokenizer=tokenizer,
                scheduler=scheduler,
            )
            self.logger.info(f"Fallback loading successful - pipeline assembled (dtype: {model_dtype})")
            
        except Exception as e:
            self.logger.error(f"Fallback loading failed: {e}")
            raise

    def _get_config_path(self) -> Optional[str]:
        """Get the path to Z-Image config files.
        
        Config files should be downloaded from HuggingFace to the base path
        following the SD_FILE_BOOTSTRAP_DATA structure.
        """
        if not hasattr(self, "path_settings") or not self.path_settings:
            return None
        
        base_path = self.path_settings.base_path
        version = "Z-Image Turbo"
        pipeline_action = "txt2img"
        if hasattr(self, "generator_settings") and self.generator_settings:
            pipeline_action = getattr(self.generator_settings, "pipeline_action", "txt2img")
        
        config_path = os.path.join(
            base_path,
            "art",
            "models",
            version,
            pipeline_action,
        )
        
        if os.path.isdir(config_path):
            return config_path
        
        # Return None - HuggingFace repo will be used directly
        return None

    def _load_zimage_scheduler(self, scheduler_path):
        """Load a flow-match scheduler with configuration based on user selection.
        
        Args:
            scheduler_path: Path to the scheduler config directory.
            
        Returns:
            Configured flow-match scheduler instance.
        """
        from diffusers import FlowMatchEulerDiscreteScheduler
        from airunner.components.art.schedulers.flow_match_scheduler_factory import (
            is_flow_match_scheduler,
            create_flow_match_scheduler,
            FLOW_MATCH_SCHEDULER_NAMES,
        )
        from airunner.enums import Scheduler
        
        # Get the scheduler name from the image request or default
        scheduler_name = None
        if hasattr(self, 'image_request') and self.image_request:
            scheduler_name = getattr(self.image_request, 'scheduler', None)
        if not scheduler_name:
            scheduler_name = Scheduler.FLOW_MATCH_EULER.value
        
        self.logger.info(f"Loading scheduler: {scheduler_name} from {scheduler_path}")
        
        # Load base config from disk but strip behavioral flags so the factory
        # can set them explicitly for the selected scheduler.
        try:
            base_scheduler = FlowMatchEulerDiscreteScheduler.from_pretrained(
                str(scheduler_path),
                local_files_only=True,
            )
            base_config = dict(base_scheduler.config)
            for flag in (
                "use_karras_sigmas",
                "stochastic_sampling",
                "use_exponential_sigmas",
                "use_beta_sigmas",
            ):
                base_config.pop(flag, None)
        except Exception as e:
            self.logger.warning(f"Could not load base scheduler config: {e}")
            base_config = None
        
        # Create the scheduler with appropriate configuration
        if is_flow_match_scheduler(scheduler_name):
            try:
                scheduler = create_flow_match_scheduler(scheduler_name, base_config)
                if hasattr(scheduler, "config"):
                    karras = scheduler.config.get("use_karras_sigmas", False)
                    stochastic = scheduler.config.get("stochastic_sampling", False)
                    self.logger.info(
                        "[ZIMAGE SCHEDULER DEBUG] %s config -> karras=%s, stochastic=%s",
                        scheduler_name,
                        karras,
                        stochastic,
                    )
                self.logger.info(
                    f"Loaded {scheduler.__class__.__name__} with config: "
                    f"{scheduler_name}"
                )
                return scheduler
            except Exception as e:
                self.logger.error(f"Failed to create scheduler {scheduler_name}: {e}")
                # Fall back to default
                self.logger.info("Falling back to default FlowMatchEulerDiscreteScheduler")
        
        # Default fallback
        if base_config:
            return FlowMatchEulerDiscreteScheduler.from_config(base_config)
        return FlowMatchEulerDiscreteScheduler()

    def _verify_pipeline_loaded(self) -> bool:
        """Verify that the pipeline was loaded correctly."""
        if self._pipe is None:
            return False
        
        required_components = ["transformer", "vae", "text_encoder", "tokenizer", "scheduler"]
        for component in required_components:
            if not hasattr(self._pipe, component) or getattr(self._pipe, component) is None:
                self.logger.warning(f"Missing required component: {component}")
                return False
        
        return True

    def _load_native_fp8_pipeline(
        self, 
        checkpoint_path: str, 
        model_dir: str, 
        pipeline_class: Any, 
        data: dict
    ) -> None:
        """Load Z-Image using native FP8 implementation.
        
        This uses our native implementation that directly handles FP8 scaled 
        checkpoints without requiring diffusers' FromOriginalModelMixin support.
        
        Key benefits:
        - Direct FP8 weight loading (no 32GB+ memory spike)
        - Streaming load for minimal CPU RAM usage
        - On-the-fly dequantization during inference
        
        Args:
            checkpoint_path: Path to the FP8 safetensors checkpoint
            model_dir: Directory containing companion files (text_encoder, vae, etc.)
            pipeline_class: The pipeline class to use for generation
            data: Additional pipeline configuration data
        """
        self.logger.info(f"Loading native FP8 pipeline from {checkpoint_path}")
        
        try:
            from airunner.components.art.managers.zimage.native import (
                ZImageNativePipeline,
            )
        except ImportError as e:
            self.logger.error(f"Native FP8 implementation not available: {e}")
            self.logger.warning("Falling back to pretrained loading with 4-bit quantization")
            self._force_quantization_for_fp8_fallback = True
            self._load_from_pretrained(model_dir, pipeline_class, data)
            return
        
        # Force memory cleanup before loading
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            # Log current VRAM state
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            self.logger.info(f"Pre-load VRAM state: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")
        
        # Get paths to companion files
        text_encoder_path = os.path.join(model_dir, "text_encoder")
        vae_path = os.path.join(model_dir, "vae")
        
        # Determine compute dtype
        model_dtype = self.data_type
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.logger.info(f"Native FP8 loading with dtype={model_dtype}, device={device}")
        
        # Create native pipeline
        native_pipeline = ZImageNativePipeline(
            transformer_path=checkpoint_path,
            text_encoder_path=text_encoder_path,
            vae_path=vae_path,
            device=device,
            dtype=model_dtype,
            text_encoder_quantization="4bit",  # Always quantize text encoder to save memory
        )
        
        # Load the transformer from FP8 checkpoint
        self.logger.info("Loading FP8 transformer weights (streaming)...")
        native_pipeline.load_transformer(stream_load=True)
        
        # Load text encoder with 4-bit quantization
        self.logger.info("Loading text encoder (4-bit quantized)...")
        native_pipeline.load_text_encoder()
        
        # Load VAE (small, no quantization needed)
        self.logger.info("Loading VAE...")
        native_pipeline.load_vae()
        
        # Store native pipeline - we'll use it directly instead of diffusers pipeline
        self._native_pipeline = native_pipeline
        
        # Create a lightweight wrapper that's compatible with the generation mixin
        self._pipe = self._create_native_pipeline_wrapper(native_pipeline, pipeline_class)
        
        self.logger.info("Native FP8 pipeline loaded successfully")
        self.logger.info(f"Memory usage: {native_pipeline.memory_usage}")

    def _create_native_pipeline_wrapper(
        self, 
        native_pipeline: Any, 
        pipeline_class: Any
    ) -> Any:
        """Create a wrapper around native pipeline for compatibility.
        
        This creates a thin wrapper that exposes the same interface as diffusers
        pipelines so the generation mixin can use it transparently.
        
        Args:
            native_pipeline: The ZImageNativePipeline instance
            pipeline_class: The target pipeline class
            
        Returns:
            A wrapped pipeline compatible with existing generation code
        """
        from airunner.components.art.managers.zimage.native.zimage_native_wrapper import (
            NativePipelineWrapper,
        )
        
        return NativePipelineWrapper(native_pipeline)

    def _swap_pipeline(self):
        """Swap between Z-Image pipeline types (txt2img <-> img2img).
        
        Z-Image pipelines share the same components (transformer, text_encoder,
        vae, tokenizer, scheduler), so we can create a new pipeline instance
        reusing the existing components without reloading from disk.
        """
        from airunner.components.art.pipelines.z_image import ZImagePipeline, ZImageImg2ImgPipeline
        
        pipeline_class = self._pipeline_class
        if pipeline_class is None:
            pipeline_class = ZImagePipeline
        
        # Check if swap is needed
        if self._pipe is None:
            self.logger.debug("No pipeline loaded, nothing to swap")
            return
        
        if self._pipe.__class__ is pipeline_class:
            self.logger.debug(f"Pipeline already is {pipeline_class.__name__}, no swap needed")
            return
        
        self.logger.info(
            f"Swapping Z-Image pipeline from {self._pipe.__class__.__name__} to {pipeline_class.__name__}"
        )
        
        try:
            # Extract components from current pipeline
            components = {
                "transformer": self._pipe.transformer,
                "text_encoder": self._pipe.text_encoder,
                "tokenizer": self._pipe.tokenizer,
                "vae": self._pipe.vae,
                "scheduler": self._pipe.scheduler,
            }
            
            # Create new pipeline with same components
            self._pipe = pipeline_class(**components)
            
            # Re-apply memory optimizations
            if hasattr(self, "_make_memory_efficient"):
                self._make_memory_efficient()
            
            self.logger.info(f"Successfully swapped to {pipeline_class.__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to swap Z-Image pipeline: {e}", exc_info=True)
            raise
