"""Helpers for resolving the live AIRunner API reference."""

from __future__ import annotations

from typing import Any


def api_from_qt_application() -> Any:
    """Compatibility shim for callers expecting the pre-split helper name."""
    return peek_registered_api()


def peek_registered_api() -> Any:
    """Return the registered service API without creating one."""
    try:
        from airunner_services.api.legacy_server import get_api

        return get_api(create_if_missing=False)
    except Exception:
        return None


def resolve_live_api_reference() -> Any:
    """Return the registered service API reference when one exists."""
    return peek_registered_api()