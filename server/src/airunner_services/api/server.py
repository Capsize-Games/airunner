"""FastAPI application setup and server configuration."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from ipaddress import ip_address
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.runtimes.bootstrap import build_runtime_registry

from .server_helpers import (
    _setup_registry_and_lifecycle,
    _setup_signal_bridges,
    _register_watchers,
    _mount_static_files,
)
from .server_middleware import (
    register_middleware,
    register_exception_handler,
    update_api_key_config,
)
from .server_routes import register_routes

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


def _default_allowed_origins() -> list[str]:
    """Return CORS origins from env, or sensible defaults per deployment mode."""
    env_origins = os.environ.get("AIRUNNER_ALLOWED_ORIGINS", "").strip()
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    mode = os.environ.get("AIRUNNER_DEPLOYMENT_MODE", "development").lower()
    if mode == "production":
        return []  # Must be set explicitly via AIRUNNER_ALLOWED_ORIGINS
    # Development mode: empty list signals "allow all loopback ports"
    return []


def _setup_cors(
    app: FastAPI,
    allowed_origins: Optional[list],
    enable_cors: bool,
) -> None:
    """Apply CORS middleware to the app."""
    if not enable_cors:
        return
    origins = (
        allowed_origins
        if allowed_origins is not None
        else _default_allowed_origins()
    )
    mode = os.environ.get("AIRUNNER_DEPLOYMENT_MODE", "development").lower()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    elif mode == "production":
        logger.warning(
            "CORS is enabled but AIRUNNER_ALLOWED_ORIGINS is not set. "
            "Set it to your frontend domain(s) in production."
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Development mode: allow any localhost or 127.0.0.1 origin
        # on any port so multiple agent client instances can coexist
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=(r"https?://(localhost|127\.0\.0\.1)(:\d+)?"),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def _load_and_apply_extensions(app: FastAPI) -> None:
    """Load extensions and apply server hooks (no-op when empty)."""
    from airunner_services.extensions.loader import (  # noqa: PLC0415
        load_extensions,
        apply_server_hooks,
    )

    load_extensions()
    apply_server_hooks(app)


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
    app.state.runtime_registry = None
    app.state.lifecycle_service = None
    _setup_registry_and_lifecycle(app, app_instance)
    _setup_signal_bridges(app_instance)
    update_api_key_config()
    _setup_cors(app, allowed_origins, enable_cors)
    # Load extensions before starting watchers: the object_storage extension's
    # ready() hook disables filesystem ingestion, and _register_watchers must
    # observe that to skip starting the directory watchers in prod.
    _load_and_apply_extensions(app)
    _register_watchers(app_instance)
    register_middleware(app)
    register_routes(app)
    _mount_static_files(app)
    register_exception_handler(app)
    return app
