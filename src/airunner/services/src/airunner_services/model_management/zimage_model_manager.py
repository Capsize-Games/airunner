"""Service-owned Z-Image model manager."""

from typing import Any, Dict, Optional

import torch

from airunner_services.model_management.model_manager_interface import (
    ModelManagerInterface,
)
from airunner_services.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner_services.art.managers.zimage.mixins.zimage_generation_mixin import (
    ZImageGenerationMixin,
)
from airunner_services.art.managers.zimage.mixins.zimage_memory_mixin import (
    ZImageMemoryMixin,
)
from airunner_services.art.managers.zimage.mixins.zimage_pipeline_loading_mixin import (
    ZImagePipelineLoadingMixin,
)
from airunner_services.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)
from airunner_services.art.pipelines.z_image import (
    ZImageImg2ImgPipeline,
    ZImagePipeline,
)
from airunner_services.art.schedulers.flow_match_scheduler_factory import (
    FLOW_MATCH_SCHEDULER_NAMES,
    create_flow_match_scheduler,
    is_flow_match_scheduler,
)
from airunner_services.contract_enums import ModelStatus, ModelType, Scheduler


class ZImageModelManager(
    ZImagePipelineLoadingMixin,
    ZImageMemoryMixin,
    ZImageGenerationMixin,
    BaseDiffusersModelManager,
    ModelManagerInterface,
):
    """Manager for Z-Image text-to-image models with memory optimizations."""

    @property
    def data_type(self) -> torch.dtype:
        """Get appropriate data type based on user settings and hardware."""
        dtype_setting = getattr(self.generator_settings, "dtype", None)

        if dtype_setting in ("4bit", "8bit", "float8"):
            if torch.cuda.is_available():
                is_bf16_supported = getattr(
                    torch.cuda,
                    "is_bf16_supported",
                    None,
                )
                if callable(is_bf16_supported) and is_bf16_supported():
                    return torch.bfloat16
                return torch.float32
            return torch.float32

        if dtype_setting == "bfloat16":
            if torch.cuda.is_available():
                is_bf16_supported = getattr(
                    torch.cuda,
                    "is_bf16_supported",
                    None,
                )
                if callable(is_bf16_supported) and is_bf16_supported():
                    return torch.bfloat16
                return torch.float32
            return torch.float32
        if dtype_setting == "float16":
            return torch.float16 if torch.cuda.is_available() else torch.float32
        if dtype_setting == "float32":
            return torch.float32

        if torch.cuda.is_available():
            is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
            if callable(is_bf16_supported) and is_bf16_supported():
                return torch.bfloat16
            return torch.float32
        return torch.float32

    @property
    def use_quantization(self) -> bool:
        """Check if quantization should be used based on dtype setting."""
        dtype_setting = getattr(self.generator_settings, "dtype", None)
        return dtype_setting in ("4bit", "8bit", "float8")

    @property
    def quantization_bits(self) -> Optional[int]:
        """Get quantization bits if quantization is enabled."""
        dtype_setting = getattr(self.generator_settings, "dtype", None)
        if dtype_setting == "4bit":
            return 4
        if dtype_setting == "8bit":
            return 8
        if dtype_setting == "float8":
            return 8
        return None

    @property
    def img2img_pipelines(self) -> tuple:
        """Get img2img pipeline classes for Z-Image."""
        if ZImageImg2ImgPipeline is not None:
            return (ZImageImg2ImgPipeline,)
        return tuple()

    @property
    def txt2img_pipelines(self) -> tuple:
        """Get txt2img pipeline classes for Z-Image."""
        if ZImagePipeline is not None:
            return (ZImagePipeline,)
        return tuple()

    @property
    def controlnet_pipelines(self) -> tuple:
        """Get ControlNet pipeline classes for Z-Image."""
        return ()

    @property
    def outpaint_pipelines(self) -> tuple:
        """Get outpaint/inpaint pipeline classes for Z-Image."""
        return ()

    @property
    def pipeline_map(self) -> Dict[str, Any]:
        """Map operation types to Z-Image pipeline classes."""
        mapping: Dict[str, Any] = {}
        if ZImagePipeline is not None:
            mapping["txt2img"] = ZImagePipeline
        if ZImageImg2ImgPipeline is not None:
            mapping["img2img"] = ZImageImg2ImgPipeline
        return mapping

    @property
    def _pipeline_class(self) -> Any:
        """Determine the appropriate pipeline class based on operation type."""
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
        """Determine if model should be loaded with from_single_file."""
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
        """Get tokenizer for prompt weighting."""
        if self._pipe and hasattr(self._pipe, "tokenizer"):
            return self._pipe.tokenizer
        return None

    @property
    def compel_text_encoder(self) -> Any:
        """Get text encoder for prompt weighting."""
        if self._pipe and hasattr(self._pipe, "text_encoder"):
            return self._pipe.text_encoder
        return None

    @property
    def use_compel(self) -> bool:
        """Disable compel for Z-Image's Qwen encoder."""
        return False

    @staticmethod
    def _is_zimage_scheduler(scheduler: Optional[Any]) -> bool:
        """Check whether the scheduler is flow-match compatible."""
        return isinstance(scheduler, FlowMatchEulerScheduler)

    def _load_scheduler(self, scheduler_name: Optional[str] = None):
        """Load the selected flow-match scheduler for Z-Image."""
        if self._pipe is None:
            return

        requested_name = (
            scheduler_name
            or (self.image_request.scheduler if self.image_request else None)
            or getattr(self, "_scheduler_name", None)
            or Scheduler.FLOW_MATCH_EULER.value
        )

        if not is_flow_match_scheduler(requested_name):
            self.logger.warning(
                f"Scheduler {requested_name} is not a flow-match scheduler. "
                f"Z-Image requires flow-match schedulers. Using default."
            )
            requested_name = Scheduler.FLOW_MATCH_EULER.value

        current_scheduler = getattr(self._pipe, "scheduler", None)
        if (
            current_scheduler is not None
            and getattr(self, "_scheduler_name", None) == requested_name
        ):
            self.logger.debug(f"Scheduler {requested_name} already loaded")
            return

        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING)

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
            self._scheduler = create_flow_match_scheduler(
                requested_name,
                base_config,
            )
            self._pipe.scheduler = self._scheduler
            self._scheduler_name = requested_name

            config_info = ""
            if hasattr(self._scheduler, "config"):
                karras = self._scheduler.config.get(
                    "use_karras_sigmas",
                    False,
                )
                stochastic = self._scheduler.config.get(
                    "stochastic_sampling",
                    False,
                )
                if karras or stochastic:
                    config_info = (
                        f" (karras={karras}, stochastic={stochastic})"
                    )

            self.logger.info(
                f"Loaded scheduler: {requested_name} -> "
                f"{self._scheduler.__class__.__name__}{config_info}"
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)

        except Exception as exc:
            self.logger.error(
                f"Failed to load Z-Image scheduler {requested_name}: {exc}",
                exc_info=True,
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)

    def _move_pipe_to_device(self):
        """Override device movement for Z-Image models with CPU offloading."""
        self.logger.debug(
            "Skipping _move_pipe_to_device for Z-Image "
            "(memory mixin handles device placement)"
        )

    @property
    def generator(self) -> torch.Generator:
        """Get the PyTorch random generator for Z-Image models."""
        if self._generator is None:
            self.logger.debug("Loading generator on CPU")
            self._generator = torch.Generator(device="cpu")
        return self._generator

    def load_model(self, *args, **kwargs) -> None:
        """Load Z-Image model."""
        return self._load_model(*args, **kwargs)

    def unload_model(self, *args, **kwargs) -> None:
        """Unload Z-Image model."""
        return self._unload_model(*args, **kwargs)

    def _load_model(self, *args, **kwargs):
        """Internal method to load Z-Image model."""
        self.load()

    def _unload_model(self, *args, **kwargs):
        """Internal method to unload Z-Image model."""
        self.unload()


__all__ = ["FLOW_MATCH_SCHEDULER_NAMES", "ZImageModelManager"]