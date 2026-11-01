"""API route modules, imported on demand to keep module imports isolated."""

from importlib import import_module
from typing import Any

__all__ = [
    "art",
    "conversations",
    "daemon",
    "downloads",
    "health",
    "legacy",
    "llm",
    "persistence",
    "stt",
    "tts",
    "tts_ws",
]


def __getattr__(name: str) -> Any:
    """Load a route module when existing callers request its package attr."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    """Include lazy route module exports in package introspection."""
    return sorted(set(globals()) | set(__all__))
