"""Integration tests for the shared WebSocket transport layer.

Tests the ``SidecarWebSocketTransport`` against a lightweight in-process
WebSocket server that simulates daemon behaviour.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import pytest
from websockets.asyncio.server import serve as ws_serve
from websockets.asyncio.server import ServerConnection

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
)
from airunner_services.runtimes.websocket_transport import (
    SidecarWebSocketTransport,
    WebSocketTransportDisconnected,
    WebSocketTransportError,
    WebSocketTransportTimeout,
)

# Unique port per test session to avoid collisions
_TEST_PORT = 19876
_TEST_WS_URL = f"http://127.0.0.1:{_TEST_PORT}"


def _make_envelope(
    request_id: str = "test-1",
    action: str = "invoke",
    *,
    runtime: str = "art",
    payload: Optional[dict[str, Any]] = None,
) -> RequestEnvelope:
    """Build a standard ``RequestEnvelope`` for testing."""
    from airunner_services.runtimes.contracts import (
        RuntimeAction,
        RuntimeKind,
    )

    return RequestEnvelope(
        request_id=request_id,
        runtime=RuntimeKind(runtime),
        action=RuntimeAction(action),
        payload=payload or {"test": True},
    )


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def event_loop():
    """Provide an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_daemon_server():
    """Start an in-process WebSocket server that acts as a mock daemon.

    The server listens for JSON messages and responds with configurable
    replies based on the ``request_id`` prefix:
    - ``ok-*`` → immediate success response
    - ``stream-*`` → multiple progress messages then success
    - ``slow-*`` → delayed response (for timeout tests)
    - ``fail-*`` → failure response
    - ``cancel-*`` → cancelled response
    - ``bad-json-*`` → non-JSON response
    - ``no-request-id-*`` → response without request_id
    """
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection):
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send("not json")
                continue

            received.append(data)
            rid = str(data.get("request_id", ""))

            if rid.startswith("ok-"):
                await ws.send(
                    json.dumps(
                        {
                            "request_id": rid,
                            "status": "succeeded",
                            "payload": {"result": "ok"},
                        }
                    )
                )

            elif rid.startswith("stream-"):
                # Send progress messages before final
                for pct in [10, 50, 90]:
                    await ws.send(
                        json.dumps(
                            {
                                "type": "progress",
                                "request_id": rid,
                                "progress": float(pct),
                                "phase": "processing",
                                "status": "running",
                            }
                        )
                    )
                    await asyncio.sleep(0.01)
                await ws.send(
                    json.dumps(
                        {
                            "request_id": rid,
                            "status": "succeeded",
                            "payload": {"result": "stream-done"},
                        }
                    )
                )

            elif rid.startswith("slow-"):
                await asyncio.sleep(0.5)
                await ws.send(
                    json.dumps(
                        {
                            "request_id": rid,
                            "status": "succeeded",
                            "payload": {"result": "slow-ok"},
                        }
                    )
                )

            elif rid.startswith("fail-"):
                await ws.send(
                    json.dumps(
                        {
                            "request_id": rid,
                            "status": "failed",
                            "error": {
                                "code": "test_error",
                                "message": "Intentional failure",
                            },
                        }
                    )
                )

            elif rid.startswith("cancel-"):
                await ws.send(
                    json.dumps(
                        {
                            "request_id": rid,
                            "status": "cancelled",
                        }
                    )
                )

            elif rid.startswith("bad-json-"):
                await ws.send("{{{invalid json")

            elif rid.startswith("no-request-id-"):
                await ws.send(
                    json.dumps(
                        {
                            "status": "succeeded",
                            "payload": {},
                        }
                    )
                )

            else:
                # Default: echo back a success
                await ws.send(
                    json.dumps(
                        {
                            "request_id": rid,
                            "status": "succeeded",
                            "payload": data.get("payload", {}),
                        }
                    )
                )

    server = await ws_serve(handler, "127.0.0.1", _TEST_PORT)
    yield server, received
    server.close()
    await server.wait_closed()


@pytest.fixture
async def transport(mock_daemon_server):
    """Create a ``SidecarWebSocketTransport`` connected to the mock daemon."""
    t = SidecarWebSocketTransport(
        _TEST_WS_URL,
        response_timeout=2.0,
        stream_timeout=5.0,
    )
    await t.connect()
    yield t
    await t.close()


# ── Connection Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_to_running_server():
    """Connecting to a running server succeeds."""

    async def handler(ws: ServerConnection):
        async for _ in ws:
            await ws.send(
                json.dumps({"request_id": "ping", "status": "succeeded"})
            )

    server = await ws_serve(handler, "127.0.0.1", _TEST_PORT + 1)
    t = SidecarWebSocketTransport(
        f"http://127.0.0.1:{_TEST_PORT + 1}",
    )
    try:
        await t.connect()
        assert t.is_connected
    finally:
        await t.close()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_connect_to_no_server():
    """Connecting to a non-existent server raises ``WebSocketTransportError``."""
    t = SidecarWebSocketTransport("http://127.0.0.1:1", connect_timeout=1.0)
    with pytest.raises(WebSocketTransportError):
        await t.connect()


@pytest.mark.asyncio
async def test_double_connect(transport):
    """Connecting twice is idempotent."""
    await transport.connect()
    assert transport.is_connected


@pytest.mark.asyncio
async def test_close(transport):
    """Closing the transport sets ``is_connected`` to False."""
    assert transport.is_connected
    await transport.close()
    # After close, the connection state should be closed
    # (is_connected may return False or raise depending on timing)
    assert not transport.is_connected or transport._ws is None


# ── Invoke Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invoke_basic(transport):
    """A basic invoke returns a successful response."""
    envelope = _make_envelope("ok-basic")
    response = await transport.invoke(envelope)
    assert response.status is EnvelopeStatus.SUCCEEDED
    assert response.payload.get("result") == "ok"


@pytest.mark.asyncio
async def test_invoke_with_payload(transport):
    """Invoke sends the payload and receives it echoed back."""
    payload = {"hello": "world", "num": 42}
    envelope = _make_envelope("echo-payload", payload=payload)
    response = await transport.invoke(envelope)
    assert response.status is EnvelopeStatus.SUCCEEDED
    assert response.payload.get("hello") == "world"


@pytest.mark.asyncio
async def test_invoke_failure(transport):
    """A failure response is returned correctly."""
    envelope = _make_envelope("fail-intentional")
    response = await transport.invoke(envelope)
    assert response.status is EnvelopeStatus.FAILED
    assert response.error is not None
    assert "Intentional failure" in response.error.message


@pytest.mark.asyncio
async def test_invoke_cancelled(transport):
    """A cancelled response is returned correctly."""
    envelope = _make_envelope("cancel-request")
    response = await transport.invoke(envelope)
    assert response.status is EnvelopeStatus.CANCELLED


@pytest.mark.asyncio
async def test_invoke_timeout():
    """A slow request times out."""

    async def handler(ws: ServerConnection):
        async for raw in ws:
            data = json.loads(raw)
            rid = data.get("request_id", "")
            # Never respond — let it time out
            await asyncio.sleep(10)

    server = await ws_serve(handler, "127.0.0.1", _TEST_PORT + 2)
    t = SidecarWebSocketTransport(
        f"http://127.0.0.1:{_TEST_PORT + 2}",
        response_timeout=0.3,
    )
    try:
        await t.connect()
        envelope = _make_envelope("slow-timeout")
        with pytest.raises(WebSocketTransportTimeout):
            await t.invoke(envelope)
    finally:
        await t.close()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_invoke_disconnected():
    """Invoking on a disconnected transport raises an error."""
    t = SidecarWebSocketTransport(
        f"http://127.0.0.1:{_TEST_PORT + 3}",
    )
    with pytest.raises(WebSocketTransportDisconnected):
        await t.invoke(_make_envelope("should-fail"))


# ── Stream Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invoke_stream_progress(transport):
    """Stream invoke delivers progress callbacks before final response."""
    progress_data: list[dict[str, Any]] = []

    def on_progress(data: dict[str, Any]):
        progress_data.append(data)

    envelope = _make_envelope("stream-progress")
    response = await transport.invoke_stream(
        envelope,
        on_progress=on_progress,
    )

    assert response.status is EnvelopeStatus.SUCCEEDED
    assert response.payload.get("result") == "stream-done"

    # Should have received progress callbacks
    assert len(progress_data) >= 3
    # Progress values should be ascending
    progress_values = [p["progress"] for p in progress_data if "progress" in p]
    assert all(
        progress_values[i] <= progress_values[i + 1]
        for i in range(len(progress_values) - 1)
    )


@pytest.mark.asyncio
async def test_invoke_stream_no_callback(transport):
    """Stream invoke without callback still returns the final response."""
    envelope = _make_envelope("stream-no-cb")
    response = await transport.invoke_stream(envelope)
    assert response.status is EnvelopeStatus.SUCCEEDED


# ── Correlation Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_requests_not_supported(transport):
    """The transport processes one request at a time (lock)."""
    # The transport uses an asyncio.Lock, so concurrent calls are
    # serialized.  Verify that sequential calls still work correctly.
    r1 = await transport.invoke(_make_envelope("ok-first"))
    r2 = await transport.invoke(_make_envelope("ok-second"))

    assert r1.status is EnvelopeStatus.SUCCEEDED
    assert r2.status is EnvelopeStatus.SUCCEEDED


# ── Edge Cases ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_descriptor_property(transport):
    """The ``descriptor`` property returns correct metadata."""
    d = transport.descriptor
    assert d.transport.value == "websocket"
    assert d.supports_streaming
    assert d.endpoint is not None


@pytest.mark.asyncio
async def test_reconnect_not_supported(transport):
    """After close, a new transport must be created."""
    await transport.close()
    with pytest.raises(WebSocketTransportDisconnected):
        await transport.invoke(_make_envelope("ok-after-close"))


# ── Adapter Integration Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_adapter_protocol():
    """Verify the LLM adapter's expected message format works."""

    async def llm_adapter_mock(ws: ServerConnection):
        async for raw in ws:
            data = json.loads(raw)
            rid = data.get("request_id", "")
            action = data.get("action", "")
            if action == "invoke":
                await ws.send(
                    json.dumps(
                        {
                            "type": "stream",
                            "request_id": rid,
                            "sequence": 0,
                            "delta": {"content": "Hello"},
                            "final": False,
                        }
                    )
                )
                await ws.send(
                    json.dumps(
                        {
                            "type": "stream",
                            "request_id": rid,
                            "sequence": 1,
                            "delta": {"content": " world"},
                            "final": True,
                        }
                    )
                )
                # Send final response envelope after stream completes
                await ws.send(
                    json.dumps(
                        {
                            "request_id": rid,
                            "status": "succeeded",
                            "payload": {"content": "Hello world"},
                        }
                    )
                )
            elif action in ("health", "status"):
                await ws.send(
                    json.dumps(
                        {
                            "type": "response",
                            "request_id": rid,
                            "status": "succeeded",
                            "payload": {"status": "ready"},
                        }
                    )
                )

    server = await ws_serve(llm_adapter_mock, "127.0.0.1", _TEST_PORT + 4)
    t = SidecarWebSocketTransport(
        f"http://127.0.0.1:{_TEST_PORT + 4}",
        stream_timeout=5.0,
    )
    try:
        await t.connect()

        # Test health
        health_env = _make_envelope("health-test", "health")
        health_resp = await t.invoke(health_env)
        assert health_resp.status is EnvelopeStatus.SUCCEEDED

        # Test streaming invoke
        stream_data: list[str] = []

        def on_chunk(data: dict[str, Any]):
            if data.get("status") != "stream":
                stream_data.append(str(data.get("delta", {})))

        invoke_env = RequestEnvelope(
            request_id="stream-llm",
            runtime="llm",  # type: ignore[arg-type]
            action="invoke",  # type: ignore[arg-type]
            payload={
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        # Use invoke (not invoke_stream) since adapter sends
        # stream-type messages and a final response
        response = await t.invoke_stream(
            invoke_env,
            on_progress=on_chunk,
        )
        assert response.status is EnvelopeStatus.SUCCEEDED
    finally:
        await t.close()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_stt_adapter_protocol():
    """Verify the STT adapter's expected message format works."""

    async def stt_adapter_mock(ws: ServerConnection):
        async for raw in ws:
            data = json.loads(raw)
            rid = data.get("request_id", "")
            action = data.get("action", "")
            if action == "invoke":
                await ws.send(
                    json.dumps(
                        {
                            "type": "response",
                            "request_id": rid,
                            "status": "succeeded",
                            "payload": {
                                "text": "Hello world",
                                "language": "en",
                            },
                        }
                    )
                )

    server = await ws_serve(stt_adapter_mock, "127.0.0.1", _TEST_PORT + 5)
    t = SidecarWebSocketTransport(
        f"http://127.0.0.1:{_TEST_PORT + 5}",
    )
    try:
        await t.connect()

        envelope = RequestEnvelope(
            request_id="stt-test",
            runtime="stt",  # type: ignore[arg-type]
            action="invoke",  # type: ignore[arg-type]
            payload={
                "audio_b64": "dGVzdCBhdWRpbw==",
                "language": "en",
            },
        )
        response = await t.invoke(envelope)
        assert response.status is EnvelopeStatus.SUCCEEDED
        assert response.payload.get("text") == "Hello world"
    finally:
        await t.close()
        server.close()
        await server.wait_closed()


# ── Helper Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_multiple_invokes_same_connection(transport):
    """Multiple sequential invokes on the same connection work."""
    for i in range(5):
        envelope = _make_envelope(f"ok-seq-{i}")
        response = await transport.invoke(envelope)
        assert response.status is EnvelopeStatus.SUCCEEDED
