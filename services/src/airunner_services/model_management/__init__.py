"""Service-owned model management helpers.

The package deliberately avoids importing torch at module import time: several
submodules (base_model_manager, hardware_profiler, memory_allocator,
model_resource_manager, model_load_balancer) import torch eagerly, and the
GUI/CI surfaces that import this package (e.g. the API route catalog) must
work without a torch install. Torch-dependent exports are resolved lazily via
``__getattr__`` (same pattern as ``airunner_services.utils.application``).
"""

from airunner_services.model_management.model_manager_interface import (
    ModelManagerInterface,
)
from airunner_services.model_management.model_registry import ModelRegistry

__all__ = [
    "BaseModelManager",
    "HardwareProfiler",
    "ModelManagerInterface",
    "QuantizationStrategy",
    "ModelRegistry",
    "MemoryAllocator",
    "ModelResourceManager",
    "ModelState",
    "CanvasMemoryTracker",
    "ModelLoadBalancer",
]


def __getattr__(name: str):
    """Resolve torch-dependent model-management exports lazily."""
    if name == "BaseModelManager":
        from airunner_services.model_management.base_model_manager import (
            BaseModelManager,
        )

        return BaseModelManager
    if name == "HardwareProfiler":
        from airunner_services.model_management.hardware_profiler import (
            HardwareProfiler,
        )

        return HardwareProfiler
    if name == "QuantizationStrategy":
        from airunner_services.model_management.quantization_strategy import (
            QuantizationStrategy,
        )

        return QuantizationStrategy
    if name == "MemoryAllocator":
        from airunner_services.model_management.memory_allocator import (
            MemoryAllocator,
        )

        return MemoryAllocator
    if name == "ModelResourceManager":
        from airunner_services.model_management.model_resource_manager import (
            ModelResourceManager,
        )

        return ModelResourceManager
    if name == "ModelState":
        from airunner_services.model_management.model_resource_manager import (
            ModelState,
        )

        return ModelState
    if name == "CanvasMemoryTracker":
        from airunner_services.model_management.canvas_memory_tracker import (
            CanvasMemoryTracker,
        )

        return CanvasMemoryTracker
    if name == "ModelLoadBalancer":
        from airunner_services.model_management.model_load_balancer import (
            ModelLoadBalancer,
        )

        return ModelLoadBalancer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
