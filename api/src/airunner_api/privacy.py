"""Transitional privacy helpers for GUI startup."""

from __future__ import annotations

from typing import Any


def activate(*args: Any, **kwargs: Any) -> Any:
    """Activate the Facehugger Shield helper via the service vendor shim."""
    from airunner_services.vendor.facehuggershield.huggingface import (
        activate as service_activate,
    )

    return service_activate(*args, **kwargs)


__all__ = ["activate"]