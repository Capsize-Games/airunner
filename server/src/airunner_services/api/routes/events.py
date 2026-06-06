"""Unified WebSocket endpoint for real-time events + RPC request/response.

Provides a single ``/api/v1/events`` WebSocket that multiplexes:

1. **Event subscriptions** — push events (model status, images, loras,
   embeddings, KB documents, index progress, download progress).
2. **RPC request/response** — replaces HTTP REST calls with WS
   messages that carry a correlation ``id`` and ``method``+``path``.
3. **Binary responses** — images and other binary data are sent as
   native WS binary frames preceded by a JSON metadata frame.

Protocol
--------
**Subscribe**::

    {"type": "subscribe", "events": ["model_status", "images"]}
    → {"type": "subscribed", "events": ["model_status", "images"]}

**RPC request**::

    {"type": "rpc", "id": "uuid", "method": "GET",
     "path": "/health", "body": {}}
    → {"type": "rpc_response", "id": "uuid", "status": 200,
       "body": {"status": "ok"}}
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket

from airunner_services.api.routes.events_bus import _WsSubscriber, WsEventBus
from airunner_services.api.routes.events_rpc import (
    ALL_EVENTS,
    EVENT_DOCUMENTS,
    EVENT_DOWNLOADS,
    EVENT_EMBEDDINGS,
    EVENT_IMAGES,
    EVENT_INDEX_PROGRESS,
    EVENT_LORAS,
    EVENT_MODEL_STATUS,
    _dispatch_rpc,
    _rpc_register,
    _rpc_routes,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _handle_subscribe(
    raw: dict[str, Any],
    websocket: WebSocket,
    subscriber: _WsSubscriber,
    bus: WsEventBus,
) -> None:
    """Process a subscribe message."""
    events: list[str] = raw.get("events", [])
    bus.subscribe(subscriber, events)
    await websocket.send_json(
        {
            "type": "subscribed",
            "events": sorted(subscriber.subscriptions),
        }
    )


async def _handle_unsubscribe(
    raw: dict[str, Any],
    websocket: WebSocket,
    subscriber: _WsSubscriber,
    bus: WsEventBus,
) -> None:
    """Process an unsubscribe message."""
    events = raw.get("events", [])
    bus.unsubscribe(subscriber, events)
    await websocket.send_json(
        {
            "type": "unsubscribed",
            "events": sorted(subscriber.subscriptions),
        }
    )


async def _send_rpc_binary(
    response: dict[str, Any],
    result: dict[str, Any],
    websocket: WebSocket,
) -> None:
    """Send an RPC response with a binary data frame."""
    response["binary"] = True
    response["headers"] = result.get("headers", {})
    await websocket.send_json(response)
    raw_body = result.get("body")
    if isinstance(raw_body, bytes):
        await websocket.send_bytes(raw_body)


async def _handle_ws_message(
    raw: dict[str, Any],
    websocket: WebSocket,
    subscriber: _WsSubscriber,
    bus: WsEventBus,
) -> None:
    """Process a single incoming WebSocket message."""
    msg_type = raw.get("type", "")

    if msg_type == "subscribe":
        await _handle_subscribe(raw, websocket, subscriber, bus)
    elif msg_type == "unsubscribe":
        await _handle_unsubscribe(raw, websocket, subscriber, bus)
    elif msg_type == "ping":
        await websocket.send_json({"type": "pong"})
    elif msg_type == "rpc":
        await _handle_rpc_message(raw, websocket)


async def _handle_rpc_message(
    raw: dict[str, Any],
    websocket: WebSocket,
) -> None:
    """Process an RPC request message and send the response."""
    rpc_id = str(raw.get("id", ""))
    method = str(raw.get("method", "GET")).upper()
    path = str(raw.get("path", "/"))
    body = raw.get("body") or {}
    result = await _dispatch_rpc(method, path, body, websocket)
    response: dict[str, Any] = {
        "type": "rpc_response",
        "id": rpc_id,
        "status": result.get("status", 500),
    }
    if "body" in result:
        response["body"] = result["body"]
    if "error" in result:
        response["error"] = result["error"]
    if result.get("binary"):
        await _send_rpc_binary(response, result, websocket)
    else:
        await websocket.send_json(response)


async def _cleanup_ws(
    subscriber: _WsSubscriber,
    drain_task: asyncio.Task,
    bus: WsEventBus,
    websocket: WebSocket,
) -> None:
    """Clean up WebSocket subscriber, drain task, and connection."""
    subscriber.close()
    drain_task.cancel()
    try:
        await drain_task
    except Exception:
        pass
    bus.remove(subscriber)
    try:
        await websocket.close()
    except Exception:
        pass


@router.websocket("/events")
async def unified_events(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time events + RPC request/response."""
    await websocket.accept()
    bus = WsEventBus()
    subscriber = _WsSubscriber(websocket)
    drain_task = asyncio.create_task(subscriber.drain_loop())

    try:
        while True:
            raw = await websocket.receive_json()
            await _handle_ws_message(raw, websocket, subscriber, bus)
    except Exception:
        pass
    finally:
        await _cleanup_ws(subscriber, drain_task, bus, websocket)


# ── Re-export for backward compatibility ─────────────────────────────────
__all__ = [
    "WsEventBus",
    "_WsSubscriber",
    "_rpc_register",
    "_rpc_routes",
    "ALL_EVENTS",
    "EVENT_IMAGES",
    "EVENT_LORAS",
    "EVENT_EMBEDDINGS",
    "EVENT_DOCUMENTS",
    "EVENT_MODEL_STATUS",
    "EVENT_INDEX_PROGRESS",
    "EVENT_DOWNLOADS",
]
