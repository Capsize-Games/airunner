"""UwUChat-compatible events socket for the desktop daemon (#2230).

The UwUChat React client does not use REST: every call is an ``rpc``
frame over one ``/api/v1/events`` WebSocket, and the server pushes a
``bootstrap`` frame on connect (see ``airunnerweb``
``client/src/features/api/WsApiClient.ts``).

Framing:

* client -> ``{"type": "rpc", "id", "method", "path", "body"}``
* server -> ``{"type": "rpc_response", "id", "status", "body"}``
* server -> ``{"type": "bootstrap", "body": {...}}``

This module is transport only; the logical paths live in
:mod:`events_handlers`. The existing API-key/loopback/Origin policy is
reused unchanged, and the loopback token is also accepted from the
query string because a browser WebSocket cannot set headers.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from airunner_services.api.routes.events_handlers import (
    bootstrap_payload,
    dispatch,
)

router = APIRouter()


def _auth_failed(ws: WebSocket) -> bool:
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


async def _handle(ws: WebSocket, msg: Dict[str, Any]) -> None:
    """Answer one ``rpc`` frame with one ``rpc_response`` frame."""
    if msg.get("type") != "rpc":
        return
    code, body = dispatch(
        str(msg.get("method", "")),
        str(msg.get("path", "")),
        msg.get("body") or {},
    )
    await ws.send_json(
        {
            "type": "rpc_response",
            "id": str(msg.get("id", "")),
            "status": code,
            "body": body,
        }
    )


@router.websocket("/events")
async def events(ws: WebSocket) -> None:
    """Serve bootstrap + RPC for the UwUChat client."""
    if _auth_failed(ws):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws.accept()
    await ws.send_json({"type": "bootstrap", "body": bootstrap_payload()})
    while True:
        try:
            msg = await ws.receive_json()
        except WebSocketDisconnect:
            return
        except ValueError:
            continue
        await _handle(ws, msg)
