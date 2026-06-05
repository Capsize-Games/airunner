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
import functools
import logging
import queue
import re
import threading
from collections import defaultdict
from typing import Any, Callable

from fastapi import APIRouter, WebSocket

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Supported event types ────────────────────────────────────────────────

EVENT_IMAGES = "images"
EVENT_LORAS = "loras"
EVENT_EMBEDDINGS = "embeddings"
EVENT_DOCUMENTS = "documents"
EVENT_MODEL_STATUS = "model_status"
EVENT_INDEX_PROGRESS = "index_progress"
EVENT_DOWNLOADS = "downloads"

ALL_EVENTS = frozenset({
    EVENT_IMAGES,
    EVENT_LORAS,
    EVENT_EMBEDDINGS,
    EVENT_DOCUMENTS,
    EVENT_MODEL_STATUS,
    EVENT_INDEX_PROGRESS,
    EVENT_DOWNLOADS,
})

# ── RPC dispatcher ───────────────────────────────────────────────────────
# Maps (method, path-pattern) to (handler, param_names).
# Path patterns use {name} syntax for path parameters.
# Handlers receive (body: dict, path_params: dict, websocket).
# and return a dict with keys: status, body, headers (optional), binary (optional).

_rpc_routes: list[tuple[str, re.Pattern, list[str], Callable]] = []
_rpc_lock = threading.Lock()


def _path_to_regex(pattern: str) -> tuple[re.Pattern, list[str]]:
    """Convert a path pattern like ``/resources/{name}/singleton``
    to a compiled regex and list of parameter names."""
    param_names: list[str] = []
    parts: list[str] = []
    for segment in pattern.split("/"):
        if segment.startswith("{") and segment.endswith("}"):
            name = segment[1:-1]
            param_names.append(name)
            parts.append(r"([^/]+)")
        else:
            parts.append(re.escape(segment))
    regex_str = "^" + "/".join(parts) + "$"
    return re.compile(regex_str), param_names


def _rpc_register(
    method: str,
    path: str,
) -> Callable:
    """Decorator that registers a handler for a (method, path) pair.

    Path may contain ``{name}`` parameters, e.g.
    ``/api/v1/settings/resources/{name}/singleton``.
    """
    pattern, param_names = _path_to_regex(path)
    def decorator(func: Callable) -> Callable:
        with _rpc_lock:
            _rpc_routes.append((method.upper(), pattern, param_names, func))
        return func
    return decorator


async def _dispatch_rpc(
    method: str,
    path: str,
    body: dict[str, Any] | None,
    websocket: WebSocket,
) -> dict[str, Any]:
    """Dispatch an RPC message to the registered handler."""
    method_upper = method.upper()
    with _rpc_lock:
        handler_entry = None
        path_params: dict[str, str] = {}
        for rpc_method, pattern, param_names, func in _rpc_routes:
            if rpc_method == method_upper:
                match = pattern.match(path)
                if match:
                    path_params = dict(zip(param_names, match.groups()))
                    handler_entry = func
                    break
    if handler_entry is None:
        return {"status": 404, "body": {"error": f"Not found: {method} {path}"}}
    try:
        kw: dict[str, Any] = {"body": body or {}, "ws": websocket}
        if path_params:
            kw["path_params"] = path_params
        result = await handler_entry(**kw)
        return result
    except Exception as exc:
        logger.exception("RPC handler error: %s %s", method, path)
        return {"status": 500, "body": {"error": str(exc)}}


# ── Built-in RPC routes ─────────────────────────────────────────────────

@_rpc_register("GET", "/health")
@_rpc_register("GET", "/api/v1/health")
async def _rpc_health(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Return server health status."""
    return {"status": 200, "body": {"status": "healthy", "service": "airunner"}}



# ── Subscriber ────────────────────────────────────────────────────────────


class _WsSubscriber:
    """One WebSocket connection registered for event delivery.

    Uses a thread-safe ``queue.Queue`` so that ``enqueue()`` can be
    called from any thread (synchronous watchdog callbacks, async signal
    handlers, etc.).  The ``drain_loop`` coroutine bridges the sync
    queue to the async WebSocket.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self._sync_queue: queue.Queue[dict[str, Any] | None] = (
            queue.Queue(maxsize=256)
        )
        self.subscriptions: set[str] = set()

    # ── Async drain ──────────────────────────────────────────────────────

    async def drain_loop(self) -> None:
        """Background task: forward queued events to the WebSocket.

        Sends a keepalive frame every 30 seconds when no events have
        been delivered to prevent proxy/lb timeouts.
        """
        loop = asyncio.get_running_loop()
        while True:
            try:
                data = await loop.run_in_executor(
                    None,
                    functools.partial(self._sync_queue.get, timeout=30),
                )
                if data is None:  # shutdown sentinel
                    break
                await self.websocket.send_json(data)
            except queue.Empty:
                try:
                    await self.websocket.send_json({"type": "keepalive"})
                except Exception:
                    break
            except Exception:
                break

    # ── Thread-safe enqueue ──────────────────────────────────────────────

    def enqueue(self, data: dict[str, Any]) -> None:
        """Enqueue one event payload (any thread)."""
        try:
            self._sync_queue.put_nowait(data)
        except queue.Full:
            pass

    def close(self) -> None:
        """Signal the drain loop to exit."""
        try:
            self._sync_queue.put_nowait(None)
        except queue.Full:
            pass


# ── Event bus ────────────────────────────────────────────────────────────


class WsEventBus:
    """Thread-safe singleton that routes events to subscribed WebSocket
    connections by event type.

    Usage::

        bus = WsEventBus()
        bus.broadcast("images", {"type": "reload"})

    The first access creates the singleton; all subsequent calls return
    the same instance.
    """

    _instance: WsEventBus | None = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> WsEventBus:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._subscribers = defaultdict(set)
                    instance._lock = threading.Lock()
                    cls._instance = instance
        return cls._instance  # type: ignore[return-value]

    # ── Subscription management ──────────────────────────────────────────

    def subscribe(
        self,
        subscriber: _WsSubscriber,
        event_types: list[str],
    ) -> None:
        """Register *subscriber* for one or more event types."""
        with self._lock:
            for et in event_types:
                if et in ALL_EVENTS:
                    self._subscribers[et].add(subscriber)
            subscriber.subscriptions.update(
                {et for et in event_types if et in ALL_EVENTS},
            )

    def unsubscribe(
        self,
        subscriber: _WsSubscriber,
        event_types: list[str],
    ) -> None:
        """Remove *subscriber* from one or more event types."""
        with self._lock:
            for et in event_types:
                self._subscribers[et].discard(subscriber)
            subscriber.subscriptions.difference_update(event_types)

    def remove(self, subscriber: _WsSubscriber) -> None:
        """Remove *subscriber* from all event types."""
        with self._lock:
            for et in list(subscriber.subscriptions):
                self._subscribers[et].discard(subscriber)
            subscriber.subscriptions.clear()

    # ── Broadcast ────────────────────────────────────────────────────────

    def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Push an event to every subscriber of *event_type*.

        Safe to call from any thread (sync or async).  Dead subscribers
        are cleaned up lazily.
        """
        with self._lock:
            subscribers = list(
                self._subscribers.get(event_type, []),
            )

        dead: list[_WsSubscriber] = []
        for sub in subscribers:
            try:
                sub.enqueue({
                    "type": "event",
                    "event": event_type,
                    "data": data,
                })
            except Exception:
                dead.append(sub)

        if dead:
            with self._lock:
                for sub in dead:
                    for et in list(sub.subscriptions):
                        self._subscribers[et].discard(sub)
                    sub.subscriptions.clear()


# ── WebSocket endpoint ───────────────────────────────────────────────────


@router.websocket("/events")
async def unified_events(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time events + RPC request/response.

    Protocol
    --------
    **Subscribe**::

        {"type": "subscribe", "events": ["model_status", "images"]}

    **Unsubscribe**::

        {"type": "unsubscribe", "events": ["loras"]}

    **RPC request** (replaces HTTP REST calls)::

        {"type": "rpc", "id": "uuid", "method": "GET",
         "path": "/health", "body": {}}

    **Ping/pong**::

        {"type": "ping"}  →  {"type": "pong"}

    The server pushes ``{"type": "event", "event": "...", "data": {...}}``
    frames for each subscribed event type, and ``{"type": "keepalive"}``
    frames every 30 seconds when idle.
    """
    await websocket.accept()
    bus = WsEventBus()
    subscriber = _WsSubscriber(websocket)
    drain_task = asyncio.create_task(subscriber.drain_loop())

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type", "")

            if msg_type == "subscribe":
                events: list[str] = raw.get("events", [])
                bus.subscribe(subscriber, events)
                await websocket.send_json({
                    "type": "subscribed",
                    "events": sorted(subscriber.subscriptions),
                })

            elif msg_type == "unsubscribe":
                events = raw.get("events", [])
                bus.unsubscribe(subscriber, events)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "events": sorted(subscriber.subscriptions),
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "rpc":
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
                    response["binary"] = True
                    response["headers"] = result.get("headers", {})
                    await websocket.send_json(response)
                    raw_body = result.get("body")
                    if isinstance(raw_body, bytes):
                        await websocket.send_bytes(raw_body)
                else:
                    await websocket.send_json(response)

    except Exception:
        pass
    finally:
        subscriber.close()
        drain_task.cancel()
        try:
            await drain_task
        except (asyncio.CancelledError, Exception):
            pass
        bus.remove(subscriber)
        try:
            await websocket.close()
        except Exception:
            pass


# ── Import RPC handlers so their @_rpc_register decorators run ──────────
# This ensures the dispatch table is populated at module load time.
from airunner_services.api.routes import rpc_handlers  # noqa: E402, F401, PLC0415
