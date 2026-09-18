"""UwUChat-compatible events socket for the desktop daemon (#2230).

The UwUChat React client does not use REST: every call is an ``rpc``
frame over one ``/api/v1/events`` WebSocket, and the server pushes a
``bootstrap`` frame on connect (see ``airunnerweb``
``client/src/features/api/WsApiClient.ts``).

Framing:

* client -> ``{"type": "rpc", "id", "method", "path", "body"}``
* server -> ``{"type": "rpc_response", "id", "status", "body"}``
* server -> ``{"type": "bootstrap", "body": {...}}``

Only an explicit allowlist of logical paths is answered; anything else
returns a 404 ``rpc_response`` rather than being interpreted. The
existing API-key/loopback-token policy is reused unchanged.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from airunner_services.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner_services.database.models.chatbot import Chatbot

router = APIRouter()

Handler = Callable[[Dict[str, Any]], Tuple[int, Any]]
_STREAM_404 = "unhandled rpc path"


def _roster() -> List[Dict[str, Any]]:
    """Return the persisted chatbots as a client-shaped roster."""
    try:
        bot = Chatbot.objects.first()
    except Exception:
        bot = None
    if bot is None:
        return []
    return [
        {
            "id": int(getattr(bot, "id", 0) or 0),
            "name": str(getattr(bot, "name", "Chatbot")),
            "botname": str(getattr(bot, "botname", "Computer")),
            "is_system_bot": False,
        }
    ]


def _bootstrap_payload() -> Dict[str, Any]:
    """Return the bootstrap body the client reads on connect."""
    return {"chatbots": _roster()}


def _health(_body: Dict[str, Any]) -> Tuple[int, Any]:
    return 200, {"status": "ok"}


def _conversations(body: Dict[str, Any]) -> Tuple[int, Any]:
    limit = int(body.get("limit", 50))
    rows = ConversationHistoryManager().list_conversations(limit=limit)
    return 200, {"conversations": rows}


def _chatbot_query(_body: Dict[str, Any]) -> Tuple[int, Any]:
    return 200, {"records": _roster()}


ROUTES: Dict[Tuple[str, str], Handler] = {
    ("GET", "/api/v1/health"): _health,
    ("GET", "/api/v1/llm/conversations"): _conversations,
    ("POST", "/api/v1/settings/resources/Chatbot/query"): _chatbot_query,
}


def dispatch(method: str, path: str, body: Dict[str, Any]) -> Tuple[int, Any]:
    """Resolve one logical RPC path against the allowlist."""
    route = path.split("?", 1)[0]
    handler = ROUTES.get((method, route))
    if handler is None:
        return 404, {"detail": f"{_STREAM_404}: {method} {route}"}
    return handler(body)


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
    await ws.send_json(
        {"type": "bootstrap", "body": _bootstrap_payload()}
    )
    while True:
        try:
            msg = await ws.receive_json()
        except WebSocketDisconnect:
            return
        except ValueError:
            continue
        await _handle(ws, msg)
