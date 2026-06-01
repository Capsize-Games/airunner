"""
Mixins for BaseDiffusersModelManager.

These mixins break down the large BaseDiffusersModelManager class into
focused, single-responsibility components for improved maintainability.
"""

from airunner_services.art.managers.stablediffusion.mixins.sd_properties_mixin import (
    SDPropertiesMixin,
)
from airunner_services.art.managers.stablediffusion.mixins.sd_pipeline_management_mixin import (
    SDPipelineManagementMixin,
)
from airunner_services.art.managers.stablediffusion.mixins.sd_model_loading_mixin import (
    SDModelLoadingMixin,
)
from airunner_services.art.managers.stablediffusion.mixins.sd_model_unloading_mixin import (
    SDModelUnloadingMixin,
)
from airunner_services.art.managers.stablediffusion.mixins.sd_memory_management_mixin import (
    SDMemoryManagementMixin,
)
from airunner_services.art.managers.stablediffusion.mixins.sd_generation_preparation_mixin import (
    SDGenerationPreparationMixin,
)
from airunner_services.art.managers.stablediffusion.mixins.sd_image_generation_mixin import (
    SDImageGenerationMixin,
)

__all__ = [
    "SDPropertiesMixin",
    "SDPipelineManagementMixin",
    "SDModelLoadingMixin",
    "SDModelUnloadingMixin",
    "SDMemoryManagementMixin",
    "SDGenerationPreparationMixin",
    "SDImageGenerationMixin",
]
