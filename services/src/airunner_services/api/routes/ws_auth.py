"""Shared authentication policy for the daemon's WebSocket surfaces.

Every daemon socket (``/api/v1/events``, ``/api/v1/llm/stream``,
``/api/v1/tts/ws``) must enforce the same API-key / loopback-token /
Origin policy. Keeping one implementation here means a new socket cannot
silently ship with a weaker check than the rest.
"""

from __future__ import annotations

from fastapi import WebSocket


def websocket_auth_failed(ws: WebSocket) -> bool:
    """Apply the shared API-key/loopback/Origin policy to one socket."""
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
    return not allowed


__all__ = ["websocket_auth_failed"]
