"""
Z-Image Model Manager for efficient image generation.

This module provides a model manager for Tongyi-MAI Z-Image models,
a 6B parameter single-stream DiT architecture optimized for high-quality
image generation with bilingual (English/Chinese) text rendering support.

Z-Image variants supported:
- Z-Image-Turbo: 8-step distilled model, sub-second inference on H800
- Z-Image-Base: Full foundation model (when released)
- Z-Image-Edit: Image editing variant (when released)

VRAM Requirements:
- ~32GB total model size unquantized
- RTX 4090/5090 (24GB): Supported with CPU offload
- RTX 4080/5080 (16GB): Supported with aggressive CPU offload
- RTX 3090 (24GB): Supported with CPU offload

Memory breakdown:
- Transformer (S3-DiT): ~24GB (6B params in bf16)
- Text encoder (Qwen2.5-VL): ~8GB
- VAE: ~168MB (bf16)
- Total: ~32GB unquantized

Key Features:
- Single-stream DiT architecture (S3-DiT) for parameter efficiency
- Accurate bilingual text rendering (English & Chinese)
- 8-step inference with Decoupled-DMD distillation
- Compatible with FlowMatchEulerDiscreteScheduler
"""

from typing import Dict, Any, Optional
import torch
from diffusers import FlowMatchEulerDiscreteScheduler

from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner.components.application.managers.base_model_manager import (
    ModelManagerInterface,
)
from airunner.components.art.managers.zimage.mixins.zimage_generation_mixin import (
    ZImageGenerationMixin,
)
from airunner.components.art.managers.zimage.mixins.zimage_memory_mixin import (
    ZImageMemoryMixin,
)
from airunner.components.art.managers.zimage.mixins.zimage_pipeline_loading_mixin import (
    ZImagePipelineLoadingMixin,
)
from airunner.enums import ModelType, ModelStatus


class ZImageModelManager(
    ZImagePipelineLoadingMixin,
    ZImageMemoryMixin,
    ZImageGenerationMixin,
    BaseDiffusersModelManager,
    ModelManagerInterface,
):
    """
    Manager for Z-Image text-to-image models with memory optimizations.

    This manager handles loading, unloading, and generating images with
    Z-Image models. It automatically applies memory optimizations based on
    available VRAM.

    Key Features:
    - Automatic CPU offload for low VRAM systems
    - bfloat16 precision by default
    - Support for single-file safetensors from CivitAI
    - Compatible with Z-Image Turbo 8-step inference

    Example:
        manager = ZImageModelManager()
        manager.load()
        image = manager.generate(prompt="A beautiful sunset over mountains")
    """

    @property
    def data_type(self) -> torch.dtype:
        """Use bfloat16 on CUDA for Z-Image.

        Returns:
            Preferred dtype for Z-Image models.
        """
        if torch.cuda.is_available():
            is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
            if callable(is_bf16_supported) and is_bf16_supported():
                return torch.bfloat16
            return torch.float32
        return torch.float32

    @property
    def img2img_pipelines(self) -> tuple:
        """Get img2img pipeline classes for Z-Image.
        
        Note: Z-Image img2img not yet available in diffusers.
        """
        return ()

    @property
    def txt2img_pipelines(self) -> tuple:
        """Get txt2img pipeline classes for Z-Image."""
        from airunner.components.art.pipelines.z_image import ZImagePipeline
        return (ZImagePipeline,)

    @property
    def controlnet_pipelines(self) -> tuple:
        """Get ControlNet pipeline classes for Z-Image.

        Note: ControlNet support for Z-Image is not yet available.
        """
        return ()

    @property
    def outpaint_pipelines(self) -> tuple:
        """Get outpaint/inpaint pipeline classes for Z-Image.
        
        Note: Z-Image-Edit not yet released.
        """
        return ()

    @property
    def pipeline_map(self) -> Dict[str, Any]:
        """Map operation types to Z-Image pipeline classes.

        Returns:
            Dict mapping operation names to pipeline classes
        """
        from airunner.components.art.pipelines.z_image import ZImagePipeline
        return {
            "txt2img": ZImagePipeline,
            # img2img, inpaint, outpaint will be added when available
        }

    @property
    def _pipeline_class(self) -> Any:
        """Determine the appropriate pipeline class based on operation type.

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
        """Determine if model should be loaded with from_single_file.

        Single-file formats (.safetensors, .ckpt) must use from_single_file.
        Directory structures use from_pretrained.

        Returns:
            True for single-file formats, False for directories
        """
        if not self.model_path:
            return False

        model_path_str = str(self.model_path).lower()
        single_file_extensions = (
            ".safetensors",
            ".ckpt",
            ".pt",
            ".bin",
        )
        return model_path_str.endswith(single_file_extensions)

    @property
    def compel_tokenizer(self) -> Any:
        """Get tokenizer for prompt weighting.

        Note: Z-Image uses Qwen tokenizer, compel may not be compatible.

        Returns:
            Tokenizer from pipeline
        """
        if self._pipe and hasattr(self._pipe, "tokenizer"):
            return self._pipe.tokenizer
        return None

    @property
    def compel_text_encoder(self) -> Any:
        """Get text encoder for prompt weighting.

        Note: Z-Image uses Qwen text encoder, compel may not be compatible.

        Returns:
            Text encoder from pipeline
        """
        if self._pipe and hasattr(self._pipe, "text_encoder"):
            return self._pipe.text_encoder
        return None

    @property
    def use_compel(self) -> bool:
        """Compel prompt weighting is not compatible with Z-Image's Qwen encoder.

        Returns:
            False to disable compel for Z-Image
        """
        return False

    @staticmethod
    def _is_zimage_scheduler(scheduler: Optional[Any]) -> bool:
        """Check whether the scheduler is already the Z-Image-compatible type."""
        return isinstance(scheduler, FlowMatchEulerDiscreteScheduler)

    def _log_scheduler_loaded(self) -> None:
        """Emit a consistent log message for scheduler readiness."""
        self.logger.info(
            "Loaded scheduler: FlowMatchEulerDiscreteScheduler (Z-Image)"
        )

    def _load_scheduler(self, scheduler_name: Optional[str] = None):
        """Ensure the active scheduler is FlowMatchEulerDiscreteScheduler."""
        if self._pipe is None:
            return

        current_scheduler = getattr(self._pipe, "scheduler", None)
        if self._is_zimage_scheduler(current_scheduler):
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
                f"Failed to load Z-Image scheduler: {exc}", exc_info=True
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)
            return

        self._pipe.scheduler = self._scheduler
        self._log_scheduler_loaded()
        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)

    def _move_pipe_to_device(self):
        """Override device movement for Z-Image models with CPU offloading."""
        self.logger.debug(
            "Skipping _move_pipe_to_device for Z-Image (memory mixin handles device placement)"
        )

    @property
    def generator(self) -> torch.Generator:
        """Get PyTorch random generator for Z-Image models.
        
        Generator must be on CPU when using enable_model_cpu_offload().
        """
        if self._generator is None:
            self.logger.debug("Loading generator on CPU")
            self._generator = torch.Generator(device="cpu")
        return self._generator

    def load_model(self, *args, **kwargs) -> None:
        """Load Z-Image model (interface method)."""
        return self._load_model(*args, **kwargs)

    def unload_model(self, *args, **kwargs) -> None:
        """Unload Z-Image model (interface method)."""
        return self._unload_model(*args, **kwargs)

    def _load_model(self, *args, **kwargs):
        """Internal method to load Z-Image model."""
        self.load()

    def _unload_model(self, *args, **kwargs):
        """Internal method to unload Z-Image model."""
        self.unload()
