"""Bounded ownership records for cancellable LLM WebSocket requests."""

from __future__ import annotations

import re
import threading
import uuid
import asyncio
import json
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocketDisconnect
from airunner_services.ipc.messages import EnvelopeStatus


_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MAX_ACTIVE_LLM_REQUESTS = 256


@dataclass(frozen=True)
class RequestOwner:
    """Authenticated caller and tenant that submitted a request."""

    principal: str
    tenant: str | None


@dataclass(frozen=True)
class ActiveLLMRequest:
    """Runtime client and owner for one live stream."""

    owner: RequestOwner
    client: Any


class ActiveLLMRequestRegistry:
    """Thread-safe, bounded index for active stream cancellation."""

    def __init__(self, max_active: int = MAX_ACTIVE_LLM_REQUESTS) -> None:
        if max_active < 1:
            raise ValueError("max_active must be positive")
        self._max_active = max_active
        self._entries: dict[str, ActiveLLMRequest] = {}
        self._lock = threading.Lock()

    def register(
        self, request_id: str, owner: RequestOwner, client: Any
    ) -> bool:
        """Register a new request unless its ID is already active or full."""
        if not valid_request_id(request_id):
            return False
        with self._lock:
            if request_id in self._entries or len(self._entries) >= self._max_active:
                return False
            self._entries[request_id] = ActiveLLMRequest(owner, client)
            return True

    def authorized_client(
        self, request_id: str, owner: RequestOwner
    ) -> Any | None:
        """Return the active client only to the request's owner."""
        with self._lock:
            entry = self._entries.get(request_id)
            if entry is None or entry.owner != owner:
                return None
            return entry.client

    def release(self, request_id: str, owner: RequestOwner) -> bool:
        """Remove one request only when the supplied owner matches."""
        with self._lock:
            entry = self._entries.get(request_id)
            if entry is None or entry.owner != owner:
                return False
            del self._entries[request_id]
            return True


def valid_request_id(value: object) -> bool:
    """Check the bounded public request identifier format."""
    return isinstance(value, str) and _REQUEST_ID.fullmatch(value) is not None


def resolve_request_id(value: object = None) -> str | None:
    """Use a validated caller ID or return ``None`` for server generation."""
    if value is None:
        return str(uuid.uuid4())
    if not valid_request_id(value):
        return None
    return value


def registry_for(app: Any) -> ActiveLLMRequestRegistry:
    """Get or install this app's active-request registry."""
    registry = getattr(app.state, "active_llm_requests", None)
    if registry is None:
        registry = ActiveLLMRequestRegistry()
        app.state.active_llm_requests = registry
    return registry


def websocket_owner(websocket: Any, tenant: str | None) -> RequestOwner:
    """Derive the stable authenticated identity used by WebSocket auth."""
    from .llm_contracts import hash_principal

    state = websocket.app.state
    if getattr(state, "require_api_key", False):
        principal = hash_principal("api_key", getattr(state, "api_key", ""))
    elif getattr(state, "insecure_no_auth", False):
        peer = getattr(getattr(websocket, "client", None), "host", "unknown")
        principal = hash_principal("insecure", str(peer))
    else:
        from airunner_services.api.loopback_token import get_or_create_loopback_token

        principal = hash_principal("loopback", get_or_create_loopback_token())
    return RequestOwner(principal, tenant)


def http_owner(request: Any, tenant: str | None) -> RequestOwner:
    """Derive the same caller identity for an authenticated HTTP action."""
    from .llm_contracts import hash_principal

    state = request.app.state
    if getattr(state, "require_api_key", False):
        principal = hash_principal("api_key", getattr(state, "api_key", ""))
    elif getattr(state, "insecure_no_auth", False):
        peer = getattr(getattr(request, "client", None), "host", "unknown")
        principal = hash_principal("insecure", str(peer))
    else:
        from airunner_services.api.loopback_token import get_or_create_loopback_token

        principal = hash_principal("loopback", get_or_create_loopback_token())
    return RequestOwner(principal, tenant)


async def receive_json_or_pending(websocket: Any, pending_events: list[dict]) -> Any:
    """Read one socket message, including a message buffered during a stream."""
    event = pending_events.pop(0) if pending_events else await websocket.receive()
    if event.get("type") == "websocket.disconnect":
        raise WebSocketDisconnect(event.get("code", 1000))
    text = event.get("text")
    if text is None and event.get("bytes") is not None:
        text = event["bytes"].decode("utf-8")
    if not isinstance(text, str):
        raise ValueError("WebSocket message must contain JSON text")
    return json.loads(text)


async def stream_owned_request(
    websocket: Any,
    client: Any,
    envelope: Any,
    request_id: str,
    owner: RequestOwner,
    frame_builder: Any,
    pending_events: list[dict],
) -> bool:
    """Run one correlated stream while observing disconnects during prefill."""
    from .llm_runtime import stream_runtime

    registry = registry_for(websocket.app)
    if not registry.register(request_id, owner, client):
        await websocket.send_json({
            "type": "error", "code": "request_id_unavailable",
            "request_id": request_id, "done": True,
        })
        return False

    async def send_stream() -> bool:
        terminal = False
        async for delta in stream_runtime(client, envelope):
            frame = frame_builder(delta)
            frame["request_id"] = request_id
            await websocket.send_json(frame)
            if delta.final or delta.status in {
                EnvelopeStatus.FAILED, EnvelopeStatus.CANCELLED
            }:
                terminal = True
                break
        return terminal

    async def watch_connection() -> bool:
        """Return True when the peer disconnects or the bounded queue closes."""
        while True:
            event = await websocket.receive()
            if event.get("type") == "websocket.disconnect":
                return True
            if len(pending_events) >= 8:
                await websocket.close(code=1008)
                return True
            pending_events.append(event)

    stream_task = asyncio.create_task(send_stream())
    receive_task = asyncio.create_task(watch_connection())
    disconnected = False
    terminal = False
    try:
        while not stream_task.done():
            done, _ = await asyncio.wait(
                {stream_task, receive_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if receive_task in done:
                # Normal messages are buffered and the observer keeps waiting.
                # Disconnects and our bounded-overflow close both terminate
                # observation, even when server-side close leaves client_state
                # CONNECTED until another ASGI event arrives.
                try:
                    observer_closed = bool(receive_task.result())
                except Exception:
                    disconnected = True
                    break
                if observer_closed or websocket.client_state.name != "CONNECTED":
                    disconnected = True
                    break
                receive_task = asyncio.create_task(watch_connection())
        if stream_task.done():
            try:
                terminal = bool(stream_task.result())
            except WebSocketDisconnect:
                disconnected = True
            except Exception:
                if websocket.client_state.name != "CONNECTED":
                    disconnected = True
                else:
                    raise
    finally:
        receive_task.cancel()
        await asyncio.gather(receive_task, return_exceptions=True)
        if not terminal:
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(client.cancel, request_id), timeout=5.0
                )
            except Exception:
                pass
        if not stream_task.done():
            stream_task.cancel()
            await asyncio.gather(stream_task, return_exceptions=True)
        registry.release(request_id, owner)
    if disconnected:
        raise WebSocketDisconnect(1000)
    return terminal
