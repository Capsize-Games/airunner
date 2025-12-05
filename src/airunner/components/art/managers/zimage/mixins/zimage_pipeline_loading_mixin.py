"""Z-Image pipeline loading mixin."""

import gc
import os
from pathlib import Path
from typing import Any, Dict, Optional

import torch

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
        # If so, prefer loading from pretrained (more reliable than single-file)
        model_path = Path(self.model_path)
        if model_path.is_file():
            model_dir = model_path.parent
        else:
            model_dir = model_path
        
        has_pretrained_structure = self._has_complete_pretrained_structure(model_dir)
        
        if has_pretrained_structure:
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

    def _load_from_single_file(self, model_path: str, pipeline_class: Any, data: Dict):
        """Load Z-Image from single safetensors file (e.g., from CivitAI).
        
        For single-file loading, the text encoder, VAE, scheduler, and tokenizer
        are loaded from the companion folders in the same directory as the 
        checkpoint file.
        
        Respects user's precision/quantization settings.
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
        
        self.logger.info(f"Precision settings - use_quantization: {use_quant}, bits: {quant_bits}, dtype: {model_dtype}")
        
        # Get the directory containing the checkpoint - companion folders
        # (text_encoder, tokenizer, vae, scheduler) are in the same directory
        model_dir = os.path.dirname(model_path)
        self.logger.info(f"Loading companion files from: {model_dir}")
        
        # Configure text encoder quantization if enabled
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
        
        # Load the text encoder from the local text_encoder subfolder
        text_encoder_path = os.path.join(model_dir, "text_encoder")
        tokenizer_path = os.path.join(model_dir, "tokenizer")
        
        quant_info = f"({quant_bits}-bit quantized)" if use_quant else f"(dtype: {model_dtype})"
        self.logger.info(f"Loading text encoder from {text_encoder_path} {quant_info}")
        try:
            load_kwargs = {
                "local_files_only": True,
            }
            if text_encoder_bnb_config is not None:
                load_kwargs["quantization_config"] = text_encoder_bnb_config
                load_kwargs["device_map"] = "auto"
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
        
        This is useful when from_single_file fails. We load each component
        separately from the local companion folders.
        
        Respects user's precision settings.
        """
        self.logger.info("Attempting fallback: manual component assembly...")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer as HFAutoTokenizer
            from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler
            from airunner.components.art.pipelines.z_image import ZImageTransformer2DModel
            
            # Get user's precision setting
            model_dtype = self.data_type
            
            # Get the directory containing the checkpoint
            model_dir = os.path.dirname(model_path)
            
            # Load the transformer from the checkpoint
            self.logger.info(f"Loading transformer from checkpoint (dtype: {model_dtype})...")
            transformer = ZImageTransformer2DModel.from_single_file(
                model_path,
                torch_dtype=model_dtype,
            )
            
            # Load VAE from local vae subfolder
            vae_path = os.path.join(model_dir, "vae")
            self.logger.info(f"Loading VAE from {vae_path}")
            vae = AutoencoderKL.from_pretrained(
                vae_path,
                torch_dtype=model_dtype,
                local_files_only=True,
            )
            
            # Load scheduler from local scheduler subfolder
            scheduler_path = os.path.join(model_dir, "scheduler")
            self.logger.info(f"Loading scheduler from {scheduler_path}")
            scheduler = FlowMatchEulerDiscreteScheduler.from_pretrained(
                scheduler_path,
                local_files_only=True,
            )
            
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

