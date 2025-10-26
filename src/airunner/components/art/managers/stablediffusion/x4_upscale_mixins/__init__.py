"""
X4 Upscale Manager Mixins.

This package contains mixins that compose the X4UpscaleManager functionality:
- Properties: Configuration and state accessors
- Pipeline Setup: Loading and configuration
- Data Preparation: Request building and validation
- Upscaling Core: Main upscaling algorithms
- Tiling: Tile building and pasting
- Image Processing: Format conversions and fallbacks
- Response: Progress and completion signaling
- Utility: Cache and error handling
"""

from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_data_preparation_mixin import (
    X4DataPreparationMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_image_processing_mixin import (
    X4ImageProcessingMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_pipeline_setup_mixin import (
    X4PipelineSetupMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_properties_mixin import (
    X4PropertiesMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_response_mixin import (
    X4ResponseMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_tiling_mixin import (
    X4TilingMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_upscaling_execution_mixin import (
    X4UpscalingExecutionMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_upscaling_tiling_mixin import (
    X4UpscalingTilingMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_upscaling_core_mixin import (
    X4UpscalingCoreMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_utility_mixin import (
    X4UtilityMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_response_io_mixin import (
    X4ResponseIOMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_data_utils_mixin import (
    X4DataUtilsMixin,
)
from airunner.components.art.managers.stablediffusion.x4_upscale_mixins.x4_oom_mixin import (
    X4OOMMixin,
)

__all__ = [
    "X4PropertiesMixin",
    "X4PipelineSetupMixin",
    "X4DataPreparationMixin",
    "X4DataUtilsMixin",
    "X4UpscalingCoreMixin",
    "X4UpscalingExecutionMixin",
    "X4UpscalingTilingMixin",
    "X4OOMMixin",
    "X4ResponseIOMixin",
    "X4TilingMixin",
    "X4ImageProcessingMixin",
    "X4ResponseMixin",
    "X4UtilityMixin",
]
