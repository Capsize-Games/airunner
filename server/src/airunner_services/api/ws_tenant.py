"""WebSocket tenant-context helper.

WebSocket connections bypass FastAPI's ``@app.middleware("http")`` stack,
so the JWT→tenant context that the auth extension establishes for HTTP
requests is *never* applied to WS handlers.  Without it, every database
operation performed while a socket is open runs against the default
(anonymous) schema — which is why chat conversations were persisted to
``tenant_anonymous`` regardless of which account was signed in.

This module decodes the access token from the WS query string (browsers
cannot set custom headers on a WS upgrade, so the client passes it as
``?token=``) and activates the matching tenant for the life of the
socket.

It degrades gracefully: if the auth extension is not installed
(single-tenant / dev mode) or no/invalid token is supplied, the
connection proceeds with no tenant override — preserving legacy
behavior rather than hard-closing the socket.
"""

from __future__ import annotations

import contextlib
from typing import Optional, Tuple

from fastapi import WebSocket

from airunner_services.data.tenant import (
    reset_tenant_key,
    set_tenant_key,
    tenant_key_from_schema,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _decode_ws_token(token: str) -> Optional[dict]:
    """Decode a JWT access token via the auth extension, if available."""
    try:
        from extensions.auth.server.jwt import decode_token
    except Exception:
        # Auth extension not installed — single-tenant / dev mode.
        return None
    try:
        return decode_token(token)
    except Exception:
        logger.debug("Failed to decode WebSocket token", exc_info=True)
        return None


def _extract_token(websocket: WebSocket) -> Optional[str]:
    """Return the bearer token from the WS query string or header."""
    token = websocket.query_params.get("token")
    if token:
        return token
    auth = websocket.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def resolve_ws_tenant(
    websocket: WebSocket,
) -> Tuple[Optional[str], Optional[int]]:
    """Return ``(raw_tenant_key, account_id)`` for an authenticated socket.

    Both values are ``None`` when the socket is unauthenticated.  The
    tenant key is the *raw* key (without the schema prefix) expected by
    :func:`set_tenant_key`.
    """
    token = _extract_token(websocket)
    if not token:
        return None, None
    payload = _decode_ws_token(token)
    if not payload or payload.get("type") != "access":
        return None, None
    tenant_key = tenant_key_from_schema(payload.get("tenant", ""))
    account_id: Optional[int] = None
    try:
        account_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        account_id = None
    return tenant_key, account_id


@contextlib.contextmanager
def ws_tenant_scope(websocket: WebSocket):
    """Activate the tenant context for an authenticated WS connection.

    Yields ``(tenant_key, account_id)``.  Restores the previous tenant
    context on exit.  When the socket is unauthenticated, no override is
    applied and ``(None, None)`` is yielded.
    """
    tenant_key, account_id = resolve_ws_tenant(websocket)
    token = set_tenant_key(tenant_key) if tenant_key else None
    try:
        yield tenant_key, account_id
    finally:
        if token is not None:
            reset_tenant_key(token)


__all__ = ["resolve_ws_tenant", "ws_tenant_scope"]
