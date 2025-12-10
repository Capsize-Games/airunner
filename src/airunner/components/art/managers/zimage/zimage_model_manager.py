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
from airunner.components.art.pipelines.z_image import (
    ZImagePipeline,
    ZImageImg2ImgPipeline,
)
import torch

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
from airunner.components.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)
from airunner.components.art.schedulers.flow_match_scheduler_factory import (
    is_flow_match_scheduler,
    create_flow_match_scheduler,
    FLOW_MATCH_SCHEDULER_NAMES,
)
from airunner.enums import Scheduler


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
        """Get appropriate data type based on user settings and hardware.

        Uses the dtype from generator_settings if available. Z-Image models
        work best with bfloat16.
        
        Note: For quantized modes (4bit, 8bit), this returns the compute dtype
        (bfloat16). The actual quantization is handled separately.
        
        Note: FP8 requests are served via 8-bit quantization for the
        transformer/text encoder to keep everything on GPU while avoiding
        CPU RAM spikes.

        Returns:
            torch.dtype based on user preference and hardware capability.
        """
        # Get dtype from settings
        dtype_setting = getattr(self.generator_settings, "dtype", None)
        
        # For quantized modes (including FP8 fallback), use bfloat16 as compute dtype
        if dtype_setting in ("4bit", "8bit", "float8"):
            if torch.cuda.is_available():
                is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
                if callable(is_bf16_supported) and is_bf16_supported():
                    return torch.bfloat16
                return torch.float32
            return torch.float32
        
        if dtype_setting == "bfloat16":
            if torch.cuda.is_available():
                is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
                if callable(is_bf16_supported) and is_bf16_supported():
                    return torch.bfloat16
                return torch.float32
            return torch.float32
        elif dtype_setting == "float16":
            return torch.float16 if torch.cuda.is_available() else torch.float32
        elif dtype_setting == "float32":
            return torch.float32
        
        # Default: bfloat16 for Z-Image
        if torch.cuda.is_available():
            is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
            if callable(is_bf16_supported) and is_bf16_supported():
                return torch.bfloat16
            return torch.float32
        return torch.float32
    
    @property
    def use_quantization(self) -> bool:
        """Check if quantization should be used based on dtype setting.
        
        Note: FP8 requests use 8-bit quantization for stability with the
        bundled text encoder.
        """
        dtype_setting = getattr(self.generator_settings, "dtype", None)
        # FP8 falls back to quantization since it's not supported
        return dtype_setting in ("4bit", "8bit", "float8")
    
    @property
    def quantization_bits(self) -> Optional[int]:
        """Get quantization bits if quantization is enabled.
        
        Note: FP8 falls back to 4-bit for Z-Image since the text encoder
        doesn't support FP8.
        """
        dtype_setting = getattr(self.generator_settings, "dtype", None)
        if dtype_setting == "4bit":
            return 4
        elif dtype_setting == "8bit":
            return 8
        elif dtype_setting == "float8":
            # Use 8-bit quantization when user requests FP8
            return 8
        return None

    @property
    def img2img_pipelines(self) -> tuple:
        """Get img2img pipeline classes for Z-Image."""
        return (ZImageImg2ImgPipeline,) if ZImageImg2ImgPipeline is not None else tuple()

    @property
    def txt2img_pipelines(self) -> tuple:
        """Get txt2img pipeline classes for Z-Image."""
        return (ZImagePipeline,) if ZImagePipeline is not None else tuple()

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
        mapping: Dict[str, Any] = {}
        if ZImagePipeline is not None:
            mapping["txt2img"] = ZImagePipeline
        if ZImageImg2ImgPipeline is not None:
            mapping["img2img"] = ZImageImg2ImgPipeline
        # inpaint, outpaint will be added when Z-Image-Edit is released
        return mapping

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
        """Check whether the scheduler is a flow-match compatible type."""
        return isinstance(scheduler, FlowMatchEulerScheduler)

    def _load_scheduler(self, scheduler_name: Optional[str] = None):
        """Load the selected flow-match scheduler for Z-Image.
        
        Args:
            scheduler_name: Display name of the scheduler to load.
                           Supports all flow-match scheduler variants.
        """
        # flow_match scheduler imports moved to module-level
        
        if self._pipe is None:
            return
        
        # Get scheduler name from request or parameter
        requested_name = (
            scheduler_name
            or (self.image_request.scheduler if self.image_request else None)
            or getattr(self, '_scheduler_name', None)
            or Scheduler.FLOW_MATCH_EULER.value
        )
        
        # Validate it's a flow-match scheduler
        if not is_flow_match_scheduler(requested_name):
            self.logger.warning(
                f"Scheduler {requested_name} is not a flow-match scheduler. "
                f"Z-Image requires flow-match schedulers. Using default."
            )
            requested_name = Scheduler.FLOW_MATCH_EULER.value
        
        # Check if we already have this scheduler loaded
        current_scheduler = getattr(self._pipe, "scheduler", None)
        if (
            current_scheduler is not None
            and getattr(self, '_scheduler_name', None) == requested_name
        ):
            self.logger.debug(f"Scheduler {requested_name} already loaded")
            return
        
        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING)
        
        # Use base config from current scheduler for structural params, but
        # strip behavioral flags so the factory sets them explicitly.
        base_config = None
        if current_scheduler is not None and hasattr(current_scheduler, "config"):
            base_config = dict(current_scheduler.config)
            for flag in (
                "use_karras_sigmas",
                "stochastic_sampling",
                "use_exponential_sigmas",
                "use_beta_sigmas",
            ):
                base_config.pop(flag, None)
        
        try:
            self._scheduler = create_flow_match_scheduler(requested_name, base_config)
            self._pipe.scheduler = self._scheduler
            self._scheduler_name = requested_name
            
            # Log what config was applied
            config_info = ""
            if hasattr(self._scheduler, 'config'):
                karras = self._scheduler.config.get('use_karras_sigmas', False)
                stochastic = self._scheduler.config.get('stochastic_sampling', False)
                if karras or stochastic:
                    config_info = f" (karras={karras}, stochastic={stochastic})"
            
            self.logger.info(
                f"Loaded scheduler: {requested_name} -> {self._scheduler.__class__.__name__}{config_info}"
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)
            
        except Exception as exc:
            self.logger.error(
                f"Failed to load Z-Image scheduler {requested_name}: {exc}", exc_info=True
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)

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
