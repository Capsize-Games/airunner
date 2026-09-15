"""Process-wide service API reference accessors.

The legacy BaseHTTPRequestHandler server used to own the module-level
``get_api``/``set_api`` accessors.  The daemon now runs exclusively on the
FastAPI surface (``airunner_services.api.server``), but several headless
runtime paths still need to resolve the registered service app instance
(e.g. LLM tool wrappers and model managers).  This module is the new home
for those accessors so nothing has to import the retired legacy server.
"""

from __future__ import annotations

from typing import Optional

from airunner_services.app.service_app import ServiceApp

# Lazy import to avoid a circular dependency at module import time.
_api: Optional[ServiceApp] = None


def _create_api_app() -> ServiceApp:
    """Create one service-owned app for headless runtime routes."""
    return ServiceApp()


def get_api(create_if_missing: bool = True) -> Optional[ServiceApp]:
    """Return the cached service app, optionally creating it on demand."""
    global _api
    if _api is None and create_if_missing:
        _api = _create_api_app()
    return _api


def set_api(api_instance: Optional[ServiceApp]) -> None:
    """Set the global API instance.

    Use this when creating an API instance manually (e.g. in headless mode)
    to ensure tools can access it via get_api().

    Args:
        api_instance: The API/App instance to register globally
    """
    global _api
    _api = api_instance


__all__ = ["get_api", "set_api"]
