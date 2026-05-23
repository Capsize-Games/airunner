"""Public model-management mixin compatibility surface."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "MemoryTrackingMixin": (
        "airunner_model.model_management.mixins.memory_tracking_mixin"
    ),
    "ModelLoadingMixin": (
        "airunner_model.model_management.mixins.model_loading_mixin"
    ),
    "ModelSelectionMixin": (
        "airunner_model.model_management.mixins.model_selection_mixin"
    ),
    "ModelStateMixin": (
        "airunner_model.model_management.mixins.model_state_mixin"
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve model-management mixins lazily."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)


def __dir__() -> list[str]:
    """Expose lazily exported model-management mixin symbols."""
    return sorted(list(globals()) + list(__all__))