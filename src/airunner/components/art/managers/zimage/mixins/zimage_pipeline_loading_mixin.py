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
        
        Uses 4-bit quantization for transformer and text encoder to reduce memory:
        - Transformer: ~5.7GB -> ~1.4GB (75% reduction)
        - Text Encoder: ~8GB -> ~2.4GB (70% reduction)
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
        
        # Configure 4-bit quantization for memory efficiency
        # NF4 (Normal Float 4) provides best quality for 4-bit
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
        
        # Load transformer with 4-bit quantization (~5.7GB -> ~1.4GB)
        transformer_path = model_dir / "transformer"
        self.logger.info(f"Loading transformer from {transformer_path} (4-bit quantized)")
        try:
            transformer = ZImageTransformer2DModel.from_pretrained(
                str(transformer_path),
                quantization_config=transformer_bnb_config,
                torch_dtype=torch.bfloat16,
                local_files_only=True,
            )
        except Exception as e:
            self.logger.error(f"Failed to load transformer: {e}")
            raise
        
        # Load text encoder with 4-bit quantization (~8GB -> ~2.4GB)
        text_encoder_path = model_dir / "text_encoder"
        tokenizer_path = model_dir / "tokenizer"
        self.logger.info(f"Loading text encoder from {text_encoder_path} (4-bit quantized)")
        try:
            text_encoder = AutoModelForCausalLM.from_pretrained(
                str(text_encoder_path),
                quantization_config=text_encoder_bnb_config,
                device_map="auto",
                local_files_only=True,
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
                torch_dtype=torch.bfloat16,
                local_files_only=True,
            )
        except Exception as e:
            self.logger.error(f"Failed to load VAE: {e}")
            raise
        
        # Load scheduler from local scheduler subfolder
        scheduler_path = model_dir / "scheduler"
        self.logger.info(f"Loading scheduler from {scheduler_path}")
        try:
            scheduler = FlowMatchEulerDiscreteScheduler.from_pretrained(
                str(scheduler_path),
                local_files_only=True,
            )
        except Exception as e:
            self.logger.error(f"Failed to load scheduler: {e}")
            raise
        
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
            self.logger.info("Pipeline assembled successfully (4-bit quantized, ~3.8GB total)")
        except Exception as e:
            self.logger.error(f"Failed to assemble pipeline: {e}")
            raise

    def _load_from_single_file(self, model_path: str, pipeline_class: Any, data: Dict):
        """Load Z-Image from single safetensors file (e.g., from CivitAI).
        
        For single-file loading, the text encoder, VAE, scheduler, and tokenizer
        are loaded from the companion folders in the same directory as the 
        checkpoint file.
        """
        self.logger.info(f"Loading Z-Image from single file: {model_path}")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler
            from airunner.components.art.pipelines.z_image import ZImageTransformer2DModel
        except ImportError as e:
            self.logger.error(f"Missing required imports: {e}")
            raise
        
        # Get the directory containing the checkpoint - companion folders
        # (text_encoder, tokenizer, vae, scheduler) are in the same directory
        model_dir = os.path.dirname(model_path)
        self.logger.info(f"Loading companion files from: {model_dir}")
        
        # Load the text encoder from the local text_encoder subfolder
        text_encoder_path = os.path.join(model_dir, "text_encoder")
        tokenizer_path = os.path.join(model_dir, "tokenizer")
        
        self.logger.info(f"Loading text encoder from {text_encoder_path}")
        try:
            text_encoder = AutoModelForCausalLM.from_pretrained(
                text_encoder_path,
                torch_dtype=torch.bfloat16,
                local_files_only=True,
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
            "torch_dtype": torch.bfloat16,
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
            self.logger.info("Pipeline loaded from single file")
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
        """
        self.logger.info("Attempting fallback: manual component assembly...")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer as HFAutoTokenizer
            from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler
            from airunner.components.art.pipelines.z_image import ZImageTransformer2DModel
            
            # Get the directory containing the checkpoint
            model_dir = os.path.dirname(model_path)
            
            # Load the transformer from the checkpoint
            self.logger.info("Loading transformer from checkpoint...")
            transformer = ZImageTransformer2DModel.from_single_file(
                model_path,
                torch_dtype=torch.bfloat16,
            )
            
            # Load VAE from local vae subfolder
            vae_path = os.path.join(model_dir, "vae")
            self.logger.info(f"Loading VAE from {vae_path}")
            vae = AutoencoderKL.from_pretrained(
                vae_path,
                torch_dtype=torch.bfloat16,
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
                    torch_dtype=torch.bfloat16,
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
            self.logger.info("Fallback loading successful - pipeline assembled from components")
            
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
