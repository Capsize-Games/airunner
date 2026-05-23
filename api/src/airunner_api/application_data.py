"""Transitional API-facing application data helpers for GUI callers."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "ShortcutKeys": (
        "airunner_services.database.models.shortcut_keys",
        "ShortcutKeys",
    ),
    "class_names": (
        "airunner_services.application_data",
        "class_names",
    ),
    "classes": (
        "airunner_services.application_data",
        "classes",
    ),
    "table_to_class": (
        "airunner_services.application_data",
        "table_to_class",
    ),
}


def __getattr__(name: str) -> Any:
    """Resolve one API-facing application-data helper lazily."""
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attribute_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return module attributes for interactive callers and tooling."""
    return sorted(set(globals()) | set(_EXPORTS))


__all__ = sorted(_EXPORTS)