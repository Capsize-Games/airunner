"""Shared authentication policy for the daemon's WebSocket surfaces.

Every daemon socket (``/api/v1/events``, ``/api/v1/llm/stream``,
``/api/v1/tts/ws``) must enforce the same API-key / loopback-token /
Origin policy. Keeping one implementation here means a new socket cannot
silently ship with a weaker check than the rest.
"""

from __future__ import annotations

import os
from contextvars import Token
from typing import Optional

from fastapi import WebSocket


def allowed_tenant_snapshot(state: object) -> set[str]:
    """Return the tenant allowlist every surface must enforce.

    Read from the snapshot captured on ``app.state`` at startup (the
    same object the HTTP tenant middleware enforces), so a redeployed
    allowlist cannot drift between HTTP and sockets. Only apps built
    before the snapshot existed fall back to parsing the environment
    per connection.
    """
    snapshot = getattr(state, "allowed_tenants", None)
    if snapshot is not None:
        return set(snapshot)
    allowed_env = (os.environ.get("AIRUNNER_ALLOWED_TENANT_KEYS") or "")
    allowed_env = allowed_env.strip()
    return {t.strip() for t in allowed_env.split(",") if t.strip()}


def scope_websocket_tenant(ws: WebSocket) -> Optional[Token]:
    """Scope DB operations to the socket's tenant headers, like HTTP.

    Mirrors the HTTP tenant middleware's gating exactly: without API-key
    auth only loopback clients may select a tenant; with API-key auth the
    key must be in the configured allowlist. Each socket runs in its own
    task, so the ContextVar set here is connection-scoped.

    Returns the context token so the socket handler can reset it on
    disconnect, or None when no tenant was selected.
    """
    from airunner_services.api.server import is_loopback_request
    from airunner_services.data.tenant import set_tenant_key

    header_value = (
        (ws.headers.get("x-tenant-key") or "").strip()
        or (ws.headers.get("x-namespace") or "").strip()
    )
    if not header_value:
        return None
    state = ws.app.state
    if getattr(state, "require_api_key", False):
        allowed_tenants = allowed_tenant_snapshot(state)
        if allowed_tenants and header_value in allowed_tenants:
            return set_tenant_key(header_value)
    elif is_loopback_request(ws):
        return set_tenant_key(header_value)
    return None


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


__all__ = [
    "allowed_tenant_snapshot",
    "scope_websocket_tenant",
    "websocket_auth_failed",
]
