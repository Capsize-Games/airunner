"""WebSocket subscriber and event bus for real-time event delivery."""

from __future__ import annotations

import asyncio
import functools
import queue
import threading
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from airunner_services.api.routes.events_rpc import ALL_EVENTS


class _WsSubscriber:
    """One WebSocket connection registered for event delivery.

    Uses a thread-safe ``queue.Queue`` so that ``enqueue()`` can be
    called from any thread (synchronous watchdog callbacks, async signal
    handlers, etc.).  The ``drain_loop`` coroutine bridges the sync
    queue to the async WebSocket.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self._sync_queue: queue.Queue[dict[str, Any] | None] = queue.Queue(
            maxsize=256
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
    _subscribers: defaultdict[str, set[_WsSubscriber]]
    _lock: threading.Lock

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

    def _cleanup_dead(self, dead: list[_WsSubscriber]) -> None:
        """Remove dead subscribers from all event types."""
        if not dead:
            return
        with self._lock:
            for sub in dead:
                for et in list(sub.subscriptions):
                    self._subscribers[et].discard(sub)
                sub.subscriptions.clear()

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
                sub.enqueue(
                    {
                        "type": "event",
                        "event": event_type,
                        "data": data,
                    }
                )
            except Exception:
                dead.append(sub)

        self._cleanup_dead(dead)
