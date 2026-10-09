"""Service-owned model management helpers.

The package deliberately avoids importing torch at module import time: several
submodules (base_model_manager, memory_allocator, model_resource_manager,
model_load_balancer) import torch eagerly, and the GUI/CI surfaces that import
this package (e.g. the API route catalog) must work without a torch install.
Torch-dependent exports are resolved lazily via ``__getattr__`` (same pattern
as ``airunner_services.utils.application``). The hardware profiler and the
prerequisite diagnostics are torch-free, so they import eagerly.
"""

from importlib import import_module
from typing import Any

from airunner_services.model_management.hardware_profiler import (
    HardwareProfiler,
    HardwareProfile,
)
from airunner_services.model_management.model_manager_interface import (
    ModelManagerInterface,
)
from airunner_services.model_management.model_registry import ModelRegistry
from airunner_services.model_management.prerequisite_types import (
    PrerequisiteCheck,
    PrerequisiteMeasurements,
    PrerequisiteReport,
    PrerequisiteStatus,
)
from airunner_services.model_management.prerequisites import (
    collect_module_versions,
    evaluate_prerequisites,
    format_report_text,
    measure_free_disk_gb,
    report_from_profile,
)

__all__ = [
    "BaseModelManager",
    "HardwareProfiler",
    "HardwareProfile",
    "ModelManagerInterface",
    "QuantizationStrategy",
    "ModelRegistry",
    "MemoryAllocator",
    "ModelResourceManager",
    "ModelState",
    "CanvasMemoryTracker",
    "ModelLoadBalancer",
    "PrerequisiteCheck",
    "PrerequisiteMeasurements",
    "PrerequisiteReport",
    "PrerequisiteStatus",
    "collect_module_versions",
    "evaluate_prerequisites",
    "format_report_text",
    "measure_free_disk_gb",
    "report_from_profile",
]


_LAZY_EXPORTS = {
    "BaseModelManager": ("base_model_manager", "BaseModelManager"),
    "QuantizationStrategy": (
        "quantization_strategy",
        "QuantizationStrategy",
    ),
    "MemoryAllocator": ("memory_allocator", "MemoryAllocator"),
    "ModelResourceManager": (
        "model_resource_manager",
        "ModelResourceManager",
    ),
    "ModelState": ("model_resource_manager", "ModelState"),
    "CanvasMemoryTracker": (
        "canvas_memory_tracker",
        "CanvasMemoryTracker",
    ),
    "ModelLoadBalancer": ("model_load_balancer", "ModelLoadBalancer"),
}


def __getattr__(name: str) -> Any:
    """Resolve torch-dependent model-management exports lazily."""
    try:
        module_name, attribute = _LAZY_EXPORTS[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None
    module = import_module(f"airunner_services.model_management.{module_name}")
    return getattr(module, attribute)
