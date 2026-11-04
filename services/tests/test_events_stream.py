"""Tests for the client-shaped ``chat`` envelope on /api/v1/llm/stream.

Proves the UwUChat client's request/response vocabulary (#2230) is served
on the same socket as the legacy desktop envelope, without changing the
legacy path:

- ``parse_client_chat`` / ``client_envelope`` validate and bound a
  ``{"type": "chat", "messages": [...]}`` frame.
- ``client_frame`` maps runtime deltas to ``chunk`` / ``error`` frames.
- A ``chat`` frame streams ``chunk`` frames ending on ``done``.
- A legacy ``{"message": "..."}`` frame still takes the legacy path.

Uses a temp SQLite database, a temp loopback token, and a fake runtime
client — no real model, network, or live-data side effects.
"""

from __future__ import annotations

import asyncio

import pytest
from starlette.testclient import TestClient

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.routes.llm_chat_envelope import (
    ClientChatError,
    client_envelope,
    client_frame,
    parse_client_chat,
    stream_client_chat,
)
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database
from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope, StreamDelta
from airunner_services.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)

_STREAM = "/api/v1/llm/stream"


class _FakeClient:
    """Deterministic runtime client: two deltas, the last one final."""

    def stream(self, envelope):
        self.last_envelope = envelope
        yield StreamDelta(
            request_id="r", delta={"content": "Hello"}, final=False
        )
        yield StreamDelta(
            request_id="r", delta={"content": " world"}, final=True
        )


class _FakeRegistry:
    """Runtime registry double resolving the fake local LLM client."""

    def __init__(self, client) -> None:
        self._client = client

    def resolve(self, kind, provider=None):
        assert kind is RuntimeKind.LLM
        return self._client


@pytest.fixture()
def isolated_token(tmp_path, monkeypatch):
    """Point the token store at a temp path and reset its cache."""
    monkeypatch.setattr(
        loopback_token,
        "loopback_token_path",
        lambda: tmp_path / "config" / "loopback_token",
    )
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None
    yield tmp_path / "config" / "loopback_token"
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """Point the ORM at a temp SQLite file."""
    db_url = f"sqlite:///{tmp_path / 'events-stream.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


def _connect(monkeypatch):
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    app = create_app()
    runtime = _FakeClient()
    runtime.descriptor = RuntimeDescriptor(
        runtime=RuntimeKind.LLM,
        provider="local",
        mode=RuntimeMode.SIDECAR,
        transport=TransportKind.HTTP,
    )
    app.state.runtime_registry = _FakeRegistry(runtime)
    token = loopback_token.get_or_create_loopback_token()
    return TestClient(app), {"X-Airunner-Token": token}


def test_parse_client_chat_rejects_empty_messages() -> None:
    with pytest.raises(ClientChatError) as exc:
        parse_client_chat({"type": "chat", "messages": []})
    assert exc.value.code == "empty_messages"


def test_parse_client_chat_maps_roles() -> None:
    messages = parse_client_chat(
        {"type": "chat", "messages": [{"role": "user", "content": "hi"}]}
    )
    assert len(messages) == 1
    assert messages[0].content == "hi"


def test_parse_client_chat_rejects_unknown_role() -> None:
    with pytest.raises(ClientChatError) as exc:
        parse_client_chat(
            {"type": "chat", "messages": [{"role": "wizard", "content": "x"}]}
        )
    assert exc.value.code == "unsupported_role"


def test_client_frame_marks_final_with_call_chain() -> None:
    delta = StreamDelta(request_id="r", delta={"content": "x"}, final=True)
    frame = client_frame(delta, "42")
    assert frame == {
        "type": "chunk",
        "request_id": "r",
        "content": "x",
        "done": True,
        "call_chain_id": "42",
    }


def test_client_frame_maps_failure_to_error() -> None:
    delta = StreamDelta(
        request_id="r",
        delta={},
        final=True,
        status=EnvelopeStatus.FAILED,
        metadata={"error": "boom"},
    )
    frame = client_frame(delta, None)
    assert frame["type"] == "error"
    assert frame["content"] == "boom"
    assert frame["done"] is True


def test_client_envelope_bounds_temperature() -> None:
    messages = parse_client_chat(
        {"type": "chat", "messages": [{"role": "user", "content": "hi"}]}
    )
    with pytest.raises(ClientChatError) as exc:
        client_envelope(messages, {"temperature": 9})
    assert exc.value.code == "temperature_out_of_bounds"


def test_stream_serves_client_chat(
    monkeypatch, isolated_token, test_db
) -> None:
    client, headers = _connect(monkeypatch)
    with client.websocket_connect(_STREAM, headers=headers) as ws:
        ws.send_json(
            {
                "type": "chat",
                "messages": [{"role": "user", "content": "hi"}],
                "conversation_id": 7,
            }
        )
        first = ws.receive_json()
        second = ws.receive_json()
    assert first["type"] == "chunk"
    assert first["content"] == "Hello"
    assert first["done"] is False
    assert first["request_id"]
    assert second["type"] == "chunk"
    assert second["content"] == " world"
    assert second["done"] is True
    assert second["call_chain_id"] == "7"


def test_stream_forwards_function_tool_messages_and_frames(
    monkeypatch,
) -> None:
    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(
        "airunner_services.api.routes.llm_runtime.asyncio.to_thread", run_inline
    )
    runtime = _FakeClient()
    runtime.descriptor = RuntimeDescriptor(
        runtime=RuntimeKind.LLM,
        provider="local",
        mode=RuntimeMode.SIDECAR,
        transport=TransportKind.HTTP,
    )
    response_call = {
        "index": 0,
        "id": "call-2",
        "type": "function",
        "function": {"name": "lookup", "arguments": '{"key":"y"}'},
    }
    def stream(envelope):
        runtime.last_envelope = envelope
        yield StreamDelta(
            request_id="r",
            delta={"content": "", "tool_calls": [response_call]},
            final=True,
            metadata={"usage": {"prompt_tokens": 4, "completion_tokens": 1}},
        )

    runtime.stream = stream
    incoming_call = {
        "id": "call-1",
        "type": "function",
        "function": {"name": "lookup", "arguments": '{"key":"x"}'},
    }
    data = {
        "type": "chat",
        "messages": [
            {"role": "assistant", "content": None, "tool_calls": [incoming_call]},
            {"role": "tool", "tool_call_id": "call-1", "content": "value: 42"},
        ],
        "tools": [
            {"type": "function", "function": {"name": "lookup", "parameters": {"type": "object"}}}
        ],
        "tool_choice": {"type": "function", "function": {"name": "lookup"}},
    }
    ws = _RecordingWebSocket()
    asyncio.run(stream_client_chat(ws, runtime, data))

    frame = ws.frames[0]
    assert frame["tool_calls"] == [response_call]
    assert frame["usage"] == {"prompt_tokens": 4, "completion_tokens": 1}
    payload = runtime.last_envelope.payload
    assert payload["tools"][0]["function"]["name"] == "lookup"
    assert payload["tool_choice"]["function"]["name"] == "lookup"
    assert payload["messages"][0]["tool_calls"] == [incoming_call]
    assert payload["messages"][1]["tool_call_id"] == "call-1"


@pytest.mark.parametrize("transport", ["http", "websocket"])
def test_authenticated_routes_preserve_function_tool_roundtrip(
    transport, monkeypatch, isolated_token, test_db
) -> None:
    client, headers = _connect(monkeypatch)
    runtime = client.app.state.runtime_registry._client
    call = {
        "id": "call-1",
        "type": "function",
        "function": {"name": "lookup", "arguments": '{"key":"x"}'},
    }
    data = {
        "messages": [
            {"role": "assistant", "content": None, "tool_calls": [call]},
            {"role": "tool", "tool_call_id": "call-1", "content": "42"},
        ],
        "tools": [{"type": "function", "function": {"name": "lookup"}}],
        "tool_choice": "auto",
    }
    usage = {"prompt_tokens": 4, "completion_tokens": 1}

    def invoke(envelope):
        runtime.last_envelope = envelope
        return ResponseEnvelope(
            request_id=envelope.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={
                "content": "", "tools": [call], "usage": usage,
                "finish_reason": "tool_calls",
            },
        )

    def stream(envelope):
        runtime.last_envelope = envelope
        yield StreamDelta(
            request_id=envelope.request_id,
            delta={"tool_calls": [call]},
            metadata={"usage": usage},
            final=True,
        )

    runtime.invoke = invoke
    runtime.stream = stream
    if transport == "http":
        response = client.post("/api/v1/llm/chat", json=data, headers=headers)
        assert response.status_code == 200, response.text
        frame = response.json()
        assert frame["finish_reason"] == "tool_calls"
    else:
        with client.websocket_connect(_STREAM, headers=headers) as ws:
            ws.send_json({"type": "chat", **data})
            frame = ws.receive_json()
        assert frame["done"] is True
    assert frame["tool_calls"] == [call]
    assert frame["usage"] == usage
    forwarded = runtime.last_envelope.payload
    assistant, result = forwarded["messages"]
    assert assistant["role"] == "assistant"
    assert assistant["content"] is None
    assert assistant["tool_calls"] == [call]
    assert result["role"] == "tool"
    assert result["content"] == "42"
    assert result["tool_call_id"] == "call-1"
    assert forwarded["tools"] == data["tools"]
    assert forwarded["tool_choice"] == "auto"


def test_stream_rejects_function_tools_for_local_fallback(
    monkeypatch,
) -> None:
    runtime = _FakeClient()
    runtime.descriptor = RuntimeDescriptor(
        runtime=RuntimeKind.LLM,
        provider="local",
        mode=RuntimeMode.SIDECAR,
        transport=TransportKind.HTTP,
    )
    runtime.descriptor = runtime.descriptor.model_copy(
        update={"mode": RuntimeMode.LOCAL_FALLBACK}
    )
    called = []
    runtime.stream = lambda envelope: called.append(envelope) or iter(())

    ws = _RecordingWebSocket()
    asyncio.run(
        stream_client_chat(
            ws,
            runtime,
            {
                "type": "chat",
                "messages": [{"role": "user", "content": "hi"}],
                "tools": [
                    {"type": "function", "function": {"name": "lookup"}}
                ],
            },
        )
    )
    frame = ws.frames[0]

    assert frame == {
        "type": "error",
        "content": "unsupported_tool_runtime",
        "done": True,
    }
    assert called == []


class _RecordingWebSocket:
    def __init__(self):
        self.frames = []

    async def send_json(self, frame):
        self.frames.append(frame)


def test_legacy_frame_path_unchanged(
    monkeypatch, isolated_token, test_db
) -> None:
    client, headers = _connect(monkeypatch)
    with client.websocket_connect(_STREAM, headers=headers) as ws:
        ws.send_json({"message": "hi", "temperature": 0.5})
        first = ws.receive_json()
        second = ws.receive_json()
    assert first["type"] == "chunk"
    assert first["content"] == "Hello"
    assert "call_chain_id" not in second
