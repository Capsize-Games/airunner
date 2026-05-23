"""Lazy access to transport-neutral request and response envelopes."""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from types import ModuleType


@lru_cache(maxsize=1)
def load_message_types() -> ModuleType:
    """Return the API module that owns envelope types."""
    return import_module("airunner_api.messages")


__all__ = ["load_message_types"]