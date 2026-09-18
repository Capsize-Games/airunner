"""Tests for the TTS WebSocket route (#2231 contract gap).

The chat client keeps a persistent ``/api/v1/tts/ws`` socket and expects
``{"type": "audio", "data": <base64>}`` back for a ``synthesize`` frame,
or ``{"type": "error", "message": ...}`` on failure. The runtime is
stubbed, so no model, network, or live data is touched.
"""

from __future__ import annotations

import base64

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.server import create_app
from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    ResponseEnvelope,
)

_WAV_BYTES = b"RIFF____WAVEfmt "


class _FakeClient:
    """Minimal TTS runtime client returning a canned envelope."""

    def __init__(self, response: ResponseEnvelope) -> None:
        self.response = response

    def invoke(self, envelope):
        """Return the canned response, recording the request payload."""
        self.envelope = envelope
        return self.response


class _FakeRegistry:
    """Registry resolving one TTS client for any deployment mode."""

    def __init__(self, client: _FakeClient) -> None:
        self.client = client

    def resolve(self, kind, provider=None, deployment_mode=None):
        """Return the single fake client."""
        return self.client


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


def _succeeded() -> ResponseEnvelope:
    return ResponseEnvelope(
        request_id="r1",
        status=EnvelopeStatus.SUCCEEDED,
        payload={
            "audio_b64": base64.b64encode(_WAV_BYTES).decode("ascii")
        },
    )


def _failed() -> ResponseEnvelope:
    return ResponseEnvelope(
        request_id="r1",
        status=EnvelopeStatus.FAILED,
        error=ErrorEnvelope(code="tts_invoke_failed", message="boom"),
    )


def _client(monkeypatch, response: ResponseEnvelope):
    """Return an authenticated TestClient with a stubbed TTS runtime."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    app = create_app()
    fake = _FakeClient(response)
    app.state.runtime_registry = _FakeRegistry(fake)
    token = loopback_token.get_or_create_loopback_token()
    return TestClient(app), {"X-Airunner-Token": token}, fake


def test_synthesize_frame_returns_base64_audio(
    monkeypatch, isolated_token
) -> None:
    """A synthesize frame answers with decoded audio bytes."""
    client, headers, fake = _client(monkeypatch, _succeeded())
    with client.websocket_connect(
        "/api/v1/tts/ws", headers=headers
    ) as ws:
        ws.send_json(
            {"type": "synthesize", "text": "hello", "speed": 1.5}
        )
        reply = ws.receive_json()
    assert reply["type"] == "audio"
    assert base64.b64decode(reply["data"]) == _WAV_BYTES
    assert fake.envelope.payload["text"] == "hello"
    assert fake.envelope.payload["speed"] == 1.5


def test_failed_synthesis_returns_an_error_frame(
    monkeypatch, isolated_token
) -> None:
    """A failed runtime call answers with an error frame."""
    client, headers, _ = _client(monkeypatch, _failed())
    with client.websocket_connect(
        "/api/v1/tts/ws", headers=headers
    ) as ws:
        ws.send_json({"type": "synthesize", "text": "hello"})
        reply = ws.receive_json()
    assert reply["type"] == "error"
    assert reply["message"] == "boom"


def test_empty_text_returns_an_error_frame(
    monkeypatch, isolated_token
) -> None:
    """Empty text is rejected without invoking the runtime."""
    client, headers, _ = _client(monkeypatch, _succeeded())
    with client.websocket_connect(
        "/api/v1/tts/ws", headers=headers
    ) as ws:
        ws.send_json({"type": "synthesize", "text": "  "})
        reply = ws.receive_json()
    assert reply == {"type": "error", "message": "text is required"}


def test_unauthenticated_socket_is_rejected(isolated_token) -> None:
    """The socket enforces the same loopback-token policy as HTTP."""
    app = create_app()
    app.state.runtime_registry = None
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/tts/ws"):
            pass
