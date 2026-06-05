"""Helpers for resolving the live AIRunner API reference."""

from __future__ import annotations

from typing import Any


def api_from_qt_application() -> Any:
    """Compatibility shim for callers expecting the pre-split helper name."""
    return peek_registered_api()


def peek_registered_api() -> Any:
    """Return the registered service API without creating one."""
    # Legacy server removed — returns None.
    # Callers should access the app through FastAPI app.state instead.
    return None


def resolve_live_api_reference() -> Any:
    """Return the registered service API reference when one exists."""
    return peek_registered_api()