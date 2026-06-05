"""Internal helpers for FastAPI app setup — imported by server.py."""

from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from airunner_services.data.tenant import reset_tenant_key, set_tenant_key
from airunner_services.runtimes.bootstrap import build_runtime_registry

_api_key_cfg: dict = {}


def _attach_existing_registry(app: FastAPI, app_instance: Any) -> bool:
    """Attach an existing runtime registry if present. Returns True if done."""
    existing = (
        getattr(app_instance, "runtime_registry", None)
        if app_instance
        else None
    )
    if existing is not None:
        app.state.runtime_registry = existing
        return True
    return False


def _build_and_attach_registry(app: FastAPI, app_instance: Any) -> None:
    """Build and attach a new runtime registry."""
    from .server import logger, _resolve_runtime_registry

    try:
        app.state.runtime_registry = build_runtime_registry(
            app_instance=app_instance,
        )
    except Exception:
        logger.exception("Failed to build runtime registry")
    if app_instance and app.state.runtime_registry is not None:
        try:
            setattr(
                app_instance,
                "runtime_registry",
                app.state.runtime_registry,
            )
        except Exception:
            logger.debug(
                "Unable to attach runtime registry to app instance",
            )
    elif app_instance:
        app.state.runtime_registry = _resolve_runtime_registry(app_instance)


def _setup_registry_and_lifecycle(app: FastAPI, app_instance: Any) -> None:
    """Attach runtime registry and lifecycle service to app state."""
    from .server import _resolve_lifecycle_service

    if not _attach_existing_registry(app, app_instance):
        _build_and_attach_registry(app, app_instance)
    if app_instance:
        app.state.airunner_app = app_instance
        app.state.lifecycle_service = _resolve_lifecycle_service(app_instance)


def _setup_signal_bridges(app_instance: Any) -> None:
    """Register index-progress and model-status bridges."""
    if app_instance is None:
        return
    from airunner_services.api.routes.knowledge_base_index import (  # noqa: PLC0415
        _register_signal_handlers,
    )
    from airunner_services.api.routes.models_status import (  # noqa: PLC0415
        _register_model_status_handlers,
    )

    _register_signal_handlers(app_instance)
    _register_model_status_handlers(app_instance)


def _register_watchers(app_instance: Any) -> None:
    """Start file-system watchers — images, loras, models."""
    if app_instance is None:
        return
    from airunner_services.api.routes.images import (  # noqa: PLC0415
        _start_watcher as _img,
    )
    from airunner_services.api.routes.lora_watch import (  # noqa: PLC0415
        _start_watcher as _lora,
    )
    from airunner_services.api.routes.embeddings_watch import (  # noqa: PLC0415
        _start_watcher as _emb,
    )
    from airunner_services.api.routes.knowledge_base_watch import (  # noqa: PLC0415
        _start_watcher as _kb,
    )
    from airunner_services.api.routes.models_watch import (  # noqa: PLC0415
        _start_watcher as _mdl,
    )

    _img()
    _lora()
    _emb()
    _kb()
    _mdl()


def _load_api_key_config() -> dict:
    api_key = (os.environ.get("AIRUNNER_API_KEY") or "").strip()
    insecure_no_auth = os.environ.get("AIRUNNER_INSECURE_NO_AUTH", "0") == "1"
    allowed_env = (
        os.environ.get("AIRUNNER_ALLOWED_TENANT_KEYS") or ""
    ).strip()
    allowed_tenants = {t.strip() for t in allowed_env.split(",") if t.strip()}
    return {
        "api_key": api_key,
        "require_api_key": bool(api_key),
        "insecure_no_auth": insecure_no_auth,
        "allowed_tenants": allowed_tenants,
    }


def _request_tenant_key(request: Request) -> str | None:
    for header in (
        "x-tenant-key",
        "x-uwuchat-namespace",
        "x-namespace",
    ):
        value = (request.headers.get(header) or "").strip()
        if value:
            return value
    return None


def _resolve_request_api_key(request: Request) -> str:
    provided = (request.headers.get("x-api-key") or "").strip()
    if not provided:
        auth = (request.headers.get("authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            provided = auth.split(" ", 1)[-1].strip()
    return provided


async def _tenant_middleware_impl(request: Request, call_next):
    """Scope DB operations to the request's tenant/namespace."""
    from .server import is_loopback_request

    header_value = _request_tenant_key(request)
    tenant_key: str | None = None
    if header_value:
        if _api_key_cfg["require_api_key"]:
            if (
                _api_key_cfg["allowed_tenants"]
                and header_value in _api_key_cfg["allowed_tenants"]
            ):
                tenant_key = header_value
        elif is_loopback_request(request):
            tenant_key = header_value
    token = set_tenant_key(tenant_key)
    try:
        return await call_next(request)
    finally:
        reset_tenant_key(token)


def _check_noauth_access(request: Request) -> bool:
    from .server import is_loopback_request

    path = request.url.path
    if path.startswith("/admin/") and not is_loopback_request(request):
        return False
    from .server import logger as _logger  # noqa: PLC0415

    if not _api_key_cfg["insecure_no_auth"] and not is_loopback_request(
        request,
    ):
        _logger.warning(
            "Rejecting non-loopback request without API key",
        )
        return False
    return True


async def _auth_middleware_impl(request: Request, call_next):
    path = request.url.path
    if path in {"/health", "/api/v1/health"}:
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    if not _api_key_cfg["require_api_key"]:
        if _check_noauth_access(request):
            return await call_next(request)
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden"},
        )
    provided = _resolve_request_api_key(request)
    if not provided or not secrets.compare_digest(
        provided,
        _api_key_cfg["api_key"],
    ):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized"},
        )
    return await call_next(request)


def update_api_key_config() -> None:
    global _api_key_cfg
    _api_key_cfg = _load_api_key_config()


def _mount_static_files(app: FastAPI) -> None:
    from .server import logger

    static_dir = os.environ.get("AIRUNNER_STATIC_DIR", "").strip()
    if not static_dir:
        return
    resolved = os.path.abspath(static_dir)
    if not os.path.isfile(os.path.join(resolved, "index.html")):
        logger.warning(
            "AIRUNNER_STATIC_DIR=%s does not contain index.html",
            resolved,
        )
        return
    logger.info(
        "Bundle mode detected — serving React frontend from %s",
        resolved,
    )
    app.mount(
        "/",
        StaticFiles(directory=resolved, html=True),
        name="web",
    )


def _register_middleware(app: FastAPI) -> None:
    """Register tenant and API key auth middleware."""

    @app.middleware("http")
    async def tenant_middleware(request, call_next):
        return await _tenant_middleware_impl(request, call_next)

    @app.middleware("http")
    async def api_key_auth_middleware(request, call_next):
        return await _auth_middleware_impl(request, call_next)


def _register_exception_handler(app: FastAPI) -> None:
    """Register the global unhandled-exception handler."""
    from .server import is_loopback_request, logger

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(
            "Unhandled exception: %s",
            exc,
            exc_info=True,
        )
        debug = os.environ.get("AIRUNNER_DEBUG", "0") == "1"
        if debug and is_loopback_request(request):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(exc),
                },
            )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )
