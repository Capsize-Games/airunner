"""Transitional privacy helpers for GUI startup."""

from __future__ import annotations

from typing import Any


def activate(*args: Any, **kwargs: Any) -> Any:
    """Activate the standalone Facehugger Shield helper."""
    from facehuggershield.huggingface import (
        activate as shield_activate,
    )

    return shield_activate(*args, **kwargs)


__all__ = ["activate"]