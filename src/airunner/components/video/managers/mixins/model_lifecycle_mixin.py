"""
Model lifecycle mixin for HunyuanVideo manager.

Handles model loading and unloading operations.
"""

import gc
from typing import Dict, Optional, Any

import torch
from transformers import (
    LlamaModel,
    CLIPTextModel,
    LlamaTokenizerFast,
    CLIPTokenizer,
    SiglipImageProcessor,
    SiglipVisionModel,
)
from diffusers import AutoencoderKLHunyuanVideo


class ModelLifecycleMixin:
    """Mixin for HunyuanVideo model loading and unloading."""

    # Model identifiers (should be defined in parent class)
    HUNYUAN_MODEL_ID: str
    FLUX_MODEL_ID: str
    TRANSFORMER_MODEL_ID: str

    def _load_text_encoders(self, gpu: torch.device) -> None:
        """Load text encoders (Llama and CLIP).

        Args:
            gpu: Target device
        """
        self._emit_progress(10, "Loading text encoders...")
        self.logger.info("Loading text encoders...")

        self.text_encoder = LlamaModel.from_pretrained(
            self.HUNYUAN_MODEL_ID,
            subfolder="text_encoder",
            torch_dtype=torch.float16,
        ).cpu()

        self.text_encoder_2 = CLIPTextModel.from_pretrained(
            self.HUNYUAN_MODEL_ID,
            subfolder="text_encoder_2",
            torch_dtype=torch.float16,
        ).cpu()

        # Load Tokenizers
        self.tokenizer = LlamaTokenizerFast.from_pretrained(
            self.HUNYUAN_MODEL_ID, subfolder="tokenizer"
        )

        self.tokenizer_2 = CLIPTokenizer.from_pretrained(
            self.HUNYUAN_MODEL_ID, subfolder="tokenizer_2"
        )

    def _load_vae(self, gpu: torch.device) -> None:
        """Load VAE encoder/decoder.

        Args:
            gpu: Target device
        """
        self._emit_progress(30, "Loading VAE...")
        self.logger.info("Loading VAE...")

        self.vae = AutoencoderKLHunyuanVideo.from_pretrained(
            self.HUNYUAN_MODEL_ID,
            subfolder="vae",
            torch_dtype=torch.float16,
        ).cpu()

    def _load_image_encoder(self, gpu: torch.device) -> None:
        """Load SiGLIP vision encoder.

        Args:
            gpu: Target device
        """
        self._emit_progress(60, "Loading vision encoder...")
        self.logger.info("Loading vision encoder...")

        self.feature_extractor = SiglipImageProcessor.from_pretrained(
            self.FLUX_MODEL_ID, subfolder="feature_extractor"
        )

        self.image_encoder = SiglipVisionModel.from_pretrained(
            self.FLUX_MODEL_ID,
            subfolder="image_encoder",
            torch_dtype=torch.float16,
        ).cpu()

    def _load_transformer(self, gpu: torch.device) -> None:
        """Load main transformer model.

        Args:
            gpu: Target device
        """
        # Import at runtime to avoid circular dependencies
        from airunner.vendor.framepack.diffusers_helper.models.hunyuan_video_packed import (
            HunyuanVideoTransformer3DModelPacked,
        )

        self._emit_progress(80, "Loading transformer...")
        self.logger.info("Loading transformer...")

        self.transformer = (
            HunyuanVideoTransformer3DModelPacked.from_pretrained(
                self.TRANSFORMER_MODEL_ID, torch_dtype=torch.bfloat16
            ).cpu()
        )

    def _configure_models(self, gpu: torch.device) -> None:
        """Configure models for inference (eval mode, dtypes, gradients).

        Args:
            gpu: Target device
        """
        # Set models to eval mode
        self.vae.eval()
        self.text_encoder.eval()
        self.text_encoder_2.eval()
        self.image_encoder.eval()
        self.transformer.eval()

        # Apply optimizations
        if not self.high_vram:
            self.vae.enable_slicing()
            self.vae.enable_tiling()
            self.logger.info("VAE slicing/tiling enabled for low VRAM")

        # High quality output
        self.transformer.high_quality_fp32_output_for_inference = True

        # Convert to target dtypes
        self.transformer.to(dtype=torch.bfloat16)
        self.vae.to(dtype=torch.float16)
        self.image_encoder.to(dtype=torch.float16)
        self.text_encoder.to(dtype=torch.float16)
        self.text_encoder_2.to(dtype=torch.float16)

        # Disable gradients
        self.vae.requires_grad_(False)
        self.text_encoder.requires_grad_(False)
        self.text_encoder_2.requires_grad_(False)
        self.image_encoder.requires_grad_(False)
        self.transformer.requires_grad_(False)

    def _initialize_teacache(self) -> None:
        """Initialize teacache if enabled."""
        if self.use_teacache:
            self._emit_progress(90, "Initializing teacache...")
            self.logger.info("Initializing teacache...")
            self.transformer.initialize_teacache(enable_teacache=True)

    def _move_models_to_device(self, gpu: torch.device) -> None:
        """Move models to target device based on VRAM mode.

        Args:
            gpu: Target device
        """
        # Import at runtime to avoid circular dependencies
        from airunner.vendor.framepack.diffusers_helper.memory import (
            DynamicSwapInstaller,
        )

        if self.high_vram:
            self.logger.info("Moving models to GPU (High VRAM mode)...")
            self.text_encoder.to(gpu)
            self.text_encoder_2.to(gpu)
            self.image_encoder.to(gpu)
            self.vae.to(gpu)
            self.transformer.to(gpu)
        else:
            # Use DynamicSwap for better memory efficiency
            self.logger.info("Installing DynamicSwap for low VRAM mode...")
            DynamicSwapInstaller.install_model(self.transformer, device=gpu)
            DynamicSwapInstaller.install_model(self.text_encoder, device=gpu)

    def _load_model(self, options: Optional[Dict[str, Any]] = None) -> bool:
        """Load the HunyuanVideo model and all components.

        Args:
            options: Configuration options (optional)
                - high_vram: Keep models in GPU memory (default: auto-detect)
                - use_teacache: Enable teacache speedup (default: True)

        Returns:
            True if successful
        """
        # Import at runtime to avoid circular dependencies
        from airunner.vendor.framepack.diffusers_helper import (
            memory as memory_utils,
        )

        options = options or {}

        try:
            self.logger.info("Loading HunyuanVideo model...")

            # Determine device and memory mode
            device_string = "cuda:0" if torch.cuda.is_available() else "cpu"
            gpu = torch.device(device_string)

            free_mem_gb = memory_utils.get_cuda_free_memory_gb(gpu)
            self.high_vram = options.get("high_vram", free_mem_gb > 60)
            self.use_teacache = options.get("use_teacache", True)

            self.logger.info(f"Free VRAM: {free_mem_gb} GB")
            self.logger.info(f"High-VRAM Mode: {self.high_vram}")

            # Load model components
            self._load_text_encoders(gpu)
            self._load_vae(gpu)
            self._load_image_encoder(gpu)
            self._load_transformer(gpu)

            # Configure models
            self._configure_models(gpu)
            self._initialize_teacache()
            self._move_models_to_device(gpu)

            self._emit_progress(100, "Model loaded successfully")
            self.logger.info("HunyuanVideo model loaded successfully")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to load HunyuanVideo model: {e}", exc_info=True
            )
            self._unload_model()
            return False

    def _unload_model(self) -> bool:
        """Unload the HunyuanVideo model and free resources.

        Returns:
            True if successful
        """
        try:
            self.logger.info("Unloading HunyuanVideo model...")

            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Unload all components
            self.text_encoder = None
            self.text_encoder_2 = None
            self.tokenizer = None
            self.tokenizer_2 = None
            self.image_encoder = None
            self.feature_extractor = None
            self.vae = None
            self.transformer = None

            # Force garbage collection
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self.logger.info("HunyuanVideo model unloaded successfully")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to unload HunyuanVideo model: {e}", exc_info=True
            )
            return False
