"""
FastAPI server implementation for AI Runner.

Provides REST and WebSocket endpoints for remote access to AI Runner's
capabilities including LLM, art generation, TTS, and STT.
"""

from __future__ import annotations

from typing import Any, Optional
from contextlib import asynccontextmanager
import os
from ipaddress import ip_address

from fastapi import FastAPI, Request

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.api.routes import events_router
from airunner_services.api.routes.health import router as health_router
from airunner_services.api.routes.art_daemon_ws import (
    router as art_daemon_ws_router,
)
from airunner_services.api.routes.art_websocket import router as art_ws_router
from airunner_services.api.routes.llm_stream_routes import (
    router as llm_ws_router,
)
from airunner_services.api.routes.tts import router as tts_router
from airunner_services.api.routes.hardware import router as hardware_ws_router
from airunner_services.api.routes.geolocation import (
    router as geolocation_router,
)
from airunner_services.api.routes.canvas_document import (
    router as canvas_ws_router,
)
from airunner_services.runtimes.bootstrap import build_runtime_registry

from .server_helpers import (
    _setup_registry_and_lifecycle,
    _setup_signal_bridges,
    _register_watchers,
    _register_middleware,
    _register_exception_handler,
    _mount_static_files,
    update_api_key_config,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def access_logs_enabled() -> bool:
    """Return whether uvicorn access logs should be emitted."""
    return os.environ.get("AIRUNNER_API_ACCESS_LOG", "0") == "1"


def _resolve_runtime_registry(app_instance: Any) -> Optional[Any]:
    """Return or create the runtime registry for an app instance."""
    registry = getattr(app_instance, "runtime_registry", None)
    if registry is not None:
        return registry
    try:
        registry = build_runtime_registry(app_instance=app_instance)
    except Exception:
        logger.exception("Failed to build runtime registry")
        return None
    try:
        setattr(app_instance, "runtime_registry", registry)
    except Exception:
        logger.debug("Unable to attach runtime registry to app instance")
    return registry


def _resolve_lifecycle_service(app_instance: Any) -> Optional[Any]:
    """Return the lifecycle service attached to an app instance."""
    return getattr(app_instance, "lifecycle_service", None)


def is_loopback_host(host: str) -> bool:
    """Return whether *host* resolves to a loopback address."""
    if not host:
        return False
    normalized = host.strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def is_loopback_request(request: Request) -> bool:
    """Return whether the request originated from a loopback address."""
    client = getattr(request, "client", None)
    if not client:
        return False
    return is_loopback_host(getattr(client, "host", ""))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown tasks."""
    logger.info("FastAPI server starting...")
    yield
    logger.info("FastAPI server shutting down...")


def create_app(
    allowed_origins: Optional[list] = None,
    enable_cors: bool = True,
    app_instance: Optional[Any] = None,
) -> FastAPI:
    """Create and configure a FastAPI application instance."""
    app = FastAPI(
        title="AI Runner API",
        version="1.0.0",
        docs_url="/docs",
        lifespan=lifespan,
    )
    app.state.update(runtime_registry=None, lifecycle_service=None)
    _setup_registry_and_lifecycle(app, app_instance)
    _setup_signal_bridges(app_instance)
    _register_watchers(app_instance)
    update_api_key_config()
    _register_middleware(app)
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(events_router, prefix="/api/v1", tags=["events"])
    app.include_router(art_ws_router, prefix="/api/v1/art", tags=["art"])
    app.include_router(llm_ws_router, prefix="/api/v1/llm", tags=["llm"])
    app.include_router(tts_router, prefix="/api/v1/tts", tags=["tts"])
    app.include_router(
        hardware_ws_router, prefix="/api/v1/daemon", tags=["daemon"]
    )
    app.include_router(
        geolocation_router, prefix="/api/v1/daemon", tags=["daemon"]
    )
    app.include_router(
        art_daemon_ws_router, prefix="/api/v1/art", tags=["art"]
    )
    app.include_router(
        canvas_ws_router, prefix="/api/v1/canvas", tags=["canvas"]
    )
    _mount_static_files(app)
    _register_exception_handler(app)
    return app
