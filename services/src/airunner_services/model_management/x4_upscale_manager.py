"""Service-owned 4x image upscaler manager."""

import gc

from diffusers import StableDiffusionUpscalePipeline

from airunner_services.model_management.model_manager_interface import (
    ModelManagerInterface,
)
from airunner_services.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner_services.art.managers.stablediffusion.x4_upscale_mixins import (
    X4DataPreparationMixin,
    X4DataUtilsMixin,
    X4ImageProcessingMixin,
    X4OOMMixin,
    X4PipelineSetupMixin,
    X4PropertiesMixin,
    X4ResponseIOMixin,
    X4ResponseMixin,
    X4TilingMixin,
    X4UpscalingCoreMixin,
    X4UpscalingExecutionMixin,
    X4UpscalingTilingMixin,
    X4UtilityMixin,
)
from airunner_services.contract_enums import ModelType
from airunner_services.utils.application.enum_resolver import (
    signal_code_member,
)


class SignalCode:
    SD_UPSCALE_SIGNAL = signal_code_member(
        "SD_UPSCALE_SIGNAL",
        signal_code_member("UPSCALE_REQUEST", "upscale_request_signal"),
    )
    SD_GENERATE_SIGNAL = signal_code_member(
        "SD_GENERATE_SIGNAL",
        signal_code_member(
            "SD_GENERATE_IMAGE_SIGNAL",
            "generate_image_signal",
        ),
    )


class X4UpscaleManager(
    BaseDiffusersModelManager,
    X4PropertiesMixin,
    X4PipelineSetupMixin,
    X4DataPreparationMixin,
    X4DataUtilsMixin,
    X4UpscalingExecutionMixin,
    X4UpscalingTilingMixin,
    X4OOMMixin,
    X4ResponseIOMixin,
    X4UpscalingCoreMixin,
    X4TilingMixin,
    X4ImageProcessingMixin,
    X4ResponseMixin,
    X4UtilityMixin,
):
    """Manage 4x image upscaling using Stable Diffusion Upscaler."""

    _pipeline_class = StableDiffusionUpscalePipeline
    model_type: ModelType = ModelType.UPSCALER

    MODEL_REPO = "stabilityai/stable-diffusion-x4-upscaler"
    SCALE_FACTOR = 4

    LOW_VRAM_TILE_SIZE = 128
    NORMAL_TILE_SIZE = 256
    TILE_OVERLAP = 16

    DEFAULT_NOISE_LEVEL = 20
    DEFAULT_GUIDANCE_SCALE = 7.5
    DEFAULT_NUM_INFERENCE_STEPS = 20
    TILE_SIZE_THRESHOLD = 512

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(
            SignalCode.SD_UPSCALE_SIGNAL,
            self.handle_upscale_request,
        )
        self.register(
            SignalCode.SD_GENERATE_SIGNAL,
            self.handle_generate_signal,
        )

    def handle_generate_signal(self, message: dict):
        """Delegate the standard SD generate path to the upscaler."""
        self.logger.debug("X4UpscaleManager received SD_GENERATE_SIGNAL")
        self.handle_upscale_request(message)

    def unload(self):
        """Unload the pipeline and free memory."""
        if hasattr(self, "pipe") and self.pipe is not None:
            del self.pipe
            self.pipe = None

        if hasattr(self, "scheduler") and self.scheduler is not None:
            del self.scheduler
            self.scheduler = None

        self._empty_cache()
        gc.collect()

        super().unload()

    def update_scheduler(self):
        """Ignore scheduler updates because the upscaler uses a fixed one."""
        pass


__all__ = ["X4UpscaleManager"]