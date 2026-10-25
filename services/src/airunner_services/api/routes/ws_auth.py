"""Shared authentication policy for the daemon's WebSocket surfaces.

Every daemon socket (``/api/v1/events``, ``/api/v1/llm/stream``,
``/api/v1/tts/ws``) must enforce the same API-key / loopback-token /
Origin policy. Keeping one implementation here means a new socket cannot
silently ship with a weaker check than the rest.
"""

from __future__ import annotations

from fastapi import WebSocket


def scope_websocket_tenant(ws: WebSocket) -> None:
    """Scope DB operations to the socket's tenant headers, like HTTP.

    Mirrors the HTTP tenant middleware's gating exactly: without API-key
    auth only loopback clients may select a tenant; with API-key auth the
    key must be in the configured allowlist. Each socket runs in its own
    task, so the ContextVar set here is connection-scoped.
    """
    from airunner_services.api.server import is_loopback_request
    from airunner_services.data.tenant import set_tenant_key

    header_value = (
        (ws.headers.get("x-tenant-key") or "").strip()
        or (ws.headers.get("x-namespace") or "").strip()
    )
    if not header_value:
        return
    state = ws.app.state
    if getattr(state, "require_api_key", False):
        import os

        allowed_env = (os.environ.get("AIRUNNER_ALLOWED_TENANT_KEYS") or "").strip()
        allowed_tenants = {t.strip() for t in allowed_env.split(",") if t.strip()}
        if allowed_tenants and header_value in allowed_tenants:
            set_tenant_key(header_value)
    elif is_loopback_request(ws):
        set_tenant_key(header_value)


def websocket_auth_failed(ws: WebSocket) -> bool:
    """Apply the shared API-key/loopback/Origin policy to one socket.

    On success also scopes the connection's tenant from its headers,
    exactly like the HTTP tenant middleware does.
    """
    from airunner_services.api.server import (
        authenticate_connection,
        is_allowed_origin,
    )

    state = ws.app.state
    origin = ws.headers.get("origin")
    if origin and not is_allowed_origin(
        origin, getattr(state, "allowed_origins", [])
    ):
        return True
    allowed, _code = authenticate_connection(
        ws,
        api_key=getattr(state, "api_key", ""),
        require_api_key=getattr(state, "require_api_key", False),
        insecure_no_auth=getattr(state, "insecure_no_auth", False),
    )
    if allowed:
        scope_websocket_tenant(ws)
    return not allowed


__all__ = ["scope_websocket_tenant", "websocket_auth_failed"]
