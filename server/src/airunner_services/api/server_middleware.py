"""Core API-key and tenant middleware."""

from __future__ import annotations

import os
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from airunner_services.data.tenant import reset_tenant_key, set_tenant_key

_api_key_cfg: dict = {}


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


def update_api_key_config() -> None:
    global _api_key_cfg
    _api_key_cfg = _load_api_key_config()


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


def _check_noauth_access(request: Request) -> bool:
    from .server import is_loopback_request

    path = request.url.path
    if path.startswith("/admin/") and not is_loopback_request(request):
        return False
    from .server import logger as _logger

    if not _api_key_cfg["insecure_no_auth"] and not is_loopback_request(
        request,
    ):
        _logger.warning(
            "Rejecting non-loopback request without API key",
        )
        return False
    return True


async def _tenant_middleware_impl(request: Request, call_next):
    """Scope DB operations to the request's tenant/namespace."""
    from .server import is_loopback_request

    header_value = _request_tenant_key(request)
    tenant_key: str | None = None
    if header_value:
        if _api_key_cfg["require_api_key"]:
            allowed = _api_key_cfg["allowed_tenants"]
            if allowed and header_value in allowed:
                tenant_key = header_value
        elif is_loopback_request(request):
            tenant_key = header_value
    token = set_tenant_key(tenant_key)
    try:
        return await call_next(request)
    finally:
        reset_tenant_key(token)


async def _auth_middleware_impl(request: Request, call_next):
    path = request.url.path
    if path in {"/health", "/api/v1/health"}:
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    if not _api_key_cfg["require_api_key"]:
        if _check_noauth_access(request):
            return await call_next(request)
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    provided = _resolve_request_api_key(request)
    if not provided or not secrets.compare_digest(
        provided,
        _api_key_cfg["api_key"],
    ):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Register tenant and API key auth middleware."""

    @app.middleware("http")
    async def tenant_middleware(request, call_next):
        return await _tenant_middleware_impl(request, call_next)

    @app.middleware("http")
    async def api_key_auth_middleware(request, call_next):
        return await _auth_middleware_impl(request, call_next)


def register_exception_handler(app: FastAPI) -> None:
    """Register the global unhandled-exception handler."""
    from .server import is_loopback_request, logger

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
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
