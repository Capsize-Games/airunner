"""Public model-management compatibility surface for the model package."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "CanvasMemoryTracker": (
        "airunner_model.model_management.canvas_memory_tracker"
    ),
    "HardwareProfiler": (
        "airunner_model.model_management.hardware_profiler"
    ),
    "MemoryAllocator": (
        "airunner_model.model_management.memory_allocator"
    ),
    "ModelManagerInterface": (
        "airunner_model.model_management.model_manager_interface"
    ),
    "ModelRegistry": "airunner_model.model_management.model_registry",
    "ModelResourceManager": (
        "airunner_model.model_management.model_resource_manager"
    ),
    "ModelState": "airunner_model.model_management.types",
    "QuantizationStrategy": (
        "airunner_model.model_management.quantization_strategy"
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve model-management exports lazily."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)


def __dir__() -> list[str]:
    """Expose lazily exported model-management symbols."""
    return sorted(list(globals()) + list(__all__))