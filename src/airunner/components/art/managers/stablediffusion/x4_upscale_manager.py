"""X4 Upscale Manager - 4x image upscaling using Stable Diffusion.

Handles 4x image upscaling with intelligent tiling for large images,
memory management, and OOM recovery. Core logic extracted to mixins
for improved maintainability.

Main responsibilities retained in this file:
- Class constants and configuration
- Signal orchestration via handle_generate_signal()

All implementation details delegated to mixins.
"""

import gc

from diffusers import StableDiffusionUpscalePipeline

from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins import (
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
)
from airunner.enums import SignalCode, ModelType


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
    """Manages 4x image upscaling using Stable Diffusion Upscaler.

    Inherits from 8 focused mixins that handle specific aspects:
    - Properties: Configuration accessors
    - Pipeline Setup: Model loading and optimization
    - Data Preparation: Request building and validation
    - Upscaling Core: Main upscaling algorithms
    - Tiling: Tile operations for large images
    - Image Processing: Format conversions
    - Response: Progress/completion/export handling
    - Utility: Cache and error helpers

    For large images (>512px), automatically tiles with overlap to prevent
    memory issues. Includes OOM recovery with adaptive tile/batch reduction.

    Attributes:
        MODEL_REPO: HuggingFace model identifier
        SCALE_FACTOR: Upscaling multiplier (4x)
        LOW_VRAM_TILE_SIZE: Tile size for low memory systems
        NORMAL_TILE_SIZE: Tile size for normal memory
        TILE_OVERLAP: Overlap between tiles in pixels
        DEFAULT_NOISE_LEVEL: Default noise for upscaling
        DEFAULT_GUIDANCE_SCALE: Default guidance scale
        DEFAULT_NUM_INFERENCE_STEPS: Default inference steps
        TILE_SIZE_THRESHOLD: Image size triggering tiling
    """

    _pipeline_class = StableDiffusionUpscalePipeline
    model_type: ModelType = ModelType.UPSCALER

    # Model configuration
    MODEL_REPO = "stabilityai/stable-diffusion-x4-upscaler"
    SCALE_FACTOR = 4

    # Tiling configuration
    LOW_VRAM_TILE_SIZE = 128
    NORMAL_TILE_SIZE = 256
    TILE_OVERLAP = 16

    # Default upscaling parameters
    DEFAULT_NOISE_LEVEL = 20
    DEFAULT_GUIDANCE_SCALE = 7.5
    DEFAULT_NUM_INFERENCE_STEPS = 20
    TILE_SIZE_THRESHOLD = 512

    def __init__(self, *args, **kwargs):
        """Initialize X4UpscaleManager.

        Args:
            *args: Positional arguments passed to parent
            **kwargs: Keyword arguments passed to parent
        """
        super().__init__(*args, **kwargs)
        self.register(
            SignalCode.SD_UPSCALE_SIGNAL, self.handle_upscale_request
        )
        self.register(
            SignalCode.SD_GENERATE_SIGNAL, self.handle_generate_signal
        )

    def handle_generate_signal(self, message: dict):
        """Handle SD_GENERATE_SIGNAL by delegating to upscaler.

        This provides compatibility with the standard SD generation pipeline
        by routing requests through the upscaling handler.

        Args:
            message: Signal payload containing:
                - data: ImageRequest or dict with request data
                - callback: Optional completion callback
                - Other upscaling parameters

        Signal Flow:
            SD_GENERATE_SIGNAL -> handle_upscale_request() -> upscaling pipeline
        """
        self.logger.debug("X4UpscaleManager received SD_GENERATE_SIGNAL")
        self.handle_upscale_request(message)

    def unload(self):
        """Unload pipeline and free memory.

        Cleans up pipeline, scheduler, and CUDA cache before calling parent
        unload. Essential for preventing memory leaks.
        """
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
        """Update scheduler configuration.

        X4 Upscaler uses fixed scheduler, so this is a no-op.
        Overrides parent to prevent scheduler changes.
        """
        pass  # X4 upscaler uses built-in scheduler
