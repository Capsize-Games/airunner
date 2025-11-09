"""
FLUX Model Manager for low VRAM inference.

This module provides a model manager for Black Forest Labs FLUX models,
optimized for low VRAM usage through CPU offloading, bfloat16 precision,
and optional quantization support.

FLUX variants supported:
- FLUX.1-dev: 12B parameter model, highest quality, requires more VRAM
- FLUX.1-schnell: Faster variant optimized for speed with fewer steps

VRAM Requirements (with text encoder quantization):
- RTX 5080 (16GB): Fully supported (~10-11GB usage with GGUF + quantized encoders)
- RTX 4090 (24GB): Full model can run in VRAM
- RTX 4080 (16GB): Fully supported (~10-11GB usage with GGUF + quantized encoders)
- RTX 3090 (24GB): Full model can run in VRAM
- RTX 3080 (12GB): Supported with CPU offload and quantization

Memory breakdown for GGUF models:
- GGUF transformer: ~8.5GB (4-bit quantized)
- T5-XXL text encoder: ~1-1.5GB (8-bit quantized, was ~4-5GB)
- CLIP text encoder: ~0.3-0.5GB (8-bit quantized, was ~1-2GB)
- VAE: ~0.3GB (bfloat16)
- Total: ~10-11GB (down from ~14-15GB without encoder quantization)

Optimizations applied:
- CPU offload: Moves model components between CPU/GPU as needed
- Text encoder quantization: 8-bit quantization saves ~4-5GB VRAM
- bfloat16 precision: Reduces VRAM usage for non-quantized components
- Sequential CPU offload: For even lower VRAM usage
- GGUF support: 4-bit quantized transformer weights
"""

from typing import Dict, Any, Optional
import torch
from diffusers import (
    FluxPipeline,
    FluxImg2ImgPipeline,
    FluxInpaintPipeline,
    FlowMatchEulerDiscreteScheduler,
)
from transformers import BitsAndBytesConfig

from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner.components.application.managers.base_model_manager import (
    ModelManagerInterface,
)
from airunner.components.art.managers.flux.mixins.flux_quantization_mixin import (
    FluxQuantizationMixin,
)
from airunner.components.art.managers.flux.mixins.flux_gguf_loading_mixin import (
    FluxGGUFLoadingMixin,
)
from airunner.components.art.managers.flux.mixins.flux_pipeline_loading_mixin import (
    FluxPipelineLoadingMixin,
)
from airunner.components.art.managers.flux.mixins.flux_memory_mixin import (
    FluxMemoryMixin,
)
from airunner.components.art.managers.flux.mixins.flux_generation_mixin import (
    FluxGenerationMixin,
)
from airunner.enums import ModelType, ModelStatus


class FluxModelManager(
    FluxQuantizationMixin,
    FluxGGUFLoadingMixin,
    FluxPipelineLoadingMixin,
    FluxMemoryMixin,
    FluxGenerationMixin,
    BaseDiffusersModelManager,
    ModelManagerInterface,
):
    """
    Manager for FLUX text-to-image models with low VRAM optimizations.

    This manager handles loading, unloading, and generating images with
    FLUX models. It automatically applies memory optimizations based on
    available VRAM.

    Key Features:
    - Automatic CPU offload for low VRAM systems
    - bfloat16 precision by default
    - Support for quantized models
    - Sequential CPU offload for minimal VRAM usage

    Example:
        manager = FluxModelManager()
        manager.load()
        image = manager.generate(prompt="A cat holding a sign")
    """

    @property
    def data_type(self) -> torch.dtype:
        """Use bfloat16 on CUDA to avoid FLUX black-image issues.

        Returns:
            Preferred dtype for FLUX models.
        """

        if torch.cuda.is_available():
            is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
            if callable(is_bf16_supported) and is_bf16_supported():
                return torch.bfloat16
            # Fallback to float32 when bfloat16 is unavailable
            return torch.float32
        return torch.float32

    @property
    def img2img_pipelines(self) -> tuple:
        """Get img2img pipeline classes for FLUX."""
        return (FluxImg2ImgPipeline,)

    @property
    def txt2img_pipelines(self) -> tuple:
        """Get txt2img pipeline classes for FLUX."""
        return (FluxPipeline,)

    @property
    def controlnet_pipelines(self) -> tuple:
        """Get ControlNet pipeline classes for FLUX.

        Note: ControlNet support for FLUX is limited as of early 2025.
        This may be updated when official support is available.
        """
        return ()

    @property
    def outpaint_pipelines(self) -> tuple:
        """Get outpaint/inpaint pipeline classes for FLUX."""
        return (FluxInpaintPipeline,)

    @property
    def pipeline_map(self) -> Dict[str, Any]:
        """
        Map operation types to FLUX pipeline classes.

        Returns:
            Dict mapping operation names to pipeline classes
        """
        return {
            "txt2img": FluxPipeline,
            "img2img": FluxImg2ImgPipeline,
            "inpaint": FluxInpaintPipeline,
            "outpaint": FluxInpaintPipeline,
        }

    @property
    def _pipeline_class(self) -> Any:
        """
        Determine the appropriate pipeline class based on operation type.

        Returns:
            Pipeline class for current operation
        """
        operation_type = "txt2img"
        if self.is_img2img:
            operation_type = "img2img"
        elif self.is_inpaint:
            operation_type = "inpaint"
        elif self.is_outpaint:
            operation_type = "outpaint"

        return self.pipeline_map.get(operation_type)

    @property
    def use_from_single_file(self) -> bool:
        """
        Determine if model should be loaded with from_single_file.

        GGUF models are single files and must use from_single_file.
        Regular FLUX models use from_pretrained.

        Returns:
            True for GGUF files, False otherwise
        """
        if self.model_path:
            return str(self.model_path).lower().endswith(".gguf")
        return False

    @property
    def compel_tokenizer(self) -> Any:
        """
        Get tokenizer for prompt weighting.

        Note: FLUX uses T5 tokenizer instead of CLIP.

        Returns:
            Tokenizer from pipeline
        """
        if self._pipe and hasattr(self._pipe, "tokenizer"):
            return self._pipe.tokenizer
        return None

    @property
    def compel_text_encoder(self) -> Any:
        """
        Get text encoder for prompt weighting.

        Note: FLUX uses T5 text encoder instead of CLIP.

        Returns:
            Text encoder from pipeline
        """
        if self._pipe and hasattr(self._pipe, "text_encoder"):
            return self._pipe.text_encoder
        return None

    @property
    def use_compel(self) -> bool:
        """
        Compel prompt weighting may not work with FLUX T5 encoder.

        Returns:
            False to disable compel for FLUX
        """
        return False

    @staticmethod
    def _is_flux_scheduler(scheduler: Optional[Any]) -> bool:
        """Check whether the scheduler is already the FLUX-compatible type."""

        return isinstance(scheduler, FlowMatchEulerDiscreteScheduler)

    def _log_scheduler_loaded(self) -> None:
        """Emit a consistent log message for scheduler readiness."""

        self.logger.info(
            "Loaded scheduler: FlowMatchEulerDiscreteScheduler (FLUX)"
        )

    def _load_scheduler(self, scheduler_name: Optional[str] = None):
        """Ensure the active scheduler is FlowMatchEulerDiscreteScheduler."""
        if self._pipe is None:
            return

        current_scheduler = getattr(self._pipe, "scheduler", None)
        if self._is_flux_scheduler(current_scheduler):
            self._log_scheduler_loaded()
            return

        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING)
        base_config = getattr(current_scheduler, "config", {})
        try:
            self._scheduler = FlowMatchEulerDiscreteScheduler.from_config(
                base_config
            )
        except Exception as exc:
            self.logger.error(
                f"Failed to load FLUX scheduler: {exc}", exc_info=True
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)
            return

        self._pipe.scheduler = self._scheduler
        self._log_scheduler_loaded()
        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)

    def _move_pipe_to_device(self):
        """Override device movement for FLUX models with CPU offloading."""
        self.logger.debug(
            "Skipping _move_pipe_to_device for FLUX (CPU offloading manages devices)"
        )
        pass

    @property
    def generator(self) -> torch.Generator:
        """Get PyTorch random generator for FLUX models with CPU offloading."""
        if self._generator is None:
            self.logger.debug("Loading generator on CPU for FLUX CPU offload")
            self._generator = torch.Generator(device="cpu")
        return self._generator

    def load_model(self, *args, **kwargs) -> None:
        """Load FLUX model (interface method)."""
        return self._load_model(*args, **kwargs)

    def unload_model(self, *args, **kwargs) -> None:
        """Unload FLUX model (interface method)."""
        return self._unload_model(*args, **kwargs)

    def _load_model(self, *args, **kwargs):
        """Internal method to load FLUX model."""
        self.load()

    def _unload_model(self, *args, **kwargs):
        """Internal method to unload FLUX model."""
        self.unload()
