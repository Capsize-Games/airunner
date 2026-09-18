"""Tests for the STT WebSocket route (#2231 STT gap).

The chat surface's STT toggle drives ``/api/v1/stt/stream``: the client
sends a JSON ``transcribe`` frame (or a raw binary audio frame) and gets
one ``transcript`` frame back. The runtime is stubbed, so no model,
network, or live data is touched.
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

_STREAM = "/api/v1/stt/stream"
_AUDIO = b"RIFF____WAVEfmt "


class _FakeClient:
    """Minimal STT runtime client returning a canned envelope."""

    def __init__(self, response: ResponseEnvelope) -> None:
        self.response = response
        self.envelopes = []

    def invoke(self, envelope):
        """Record the request and return the canned response."""
        self.envelopes.append(envelope)
        return self.response


class _FakeRegistry:
    """Registry resolving one STT client."""

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


def _transcript(text: str = "hello world") -> ResponseEnvelope:
    return ResponseEnvelope(
        request_id="r1",
        status=EnvelopeStatus.SUCCEEDED,
        payload={"text": text, "language": "en"},
    )


def _failed() -> ResponseEnvelope:
    return ResponseEnvelope(
        request_id="r1",
        status=EnvelopeStatus.FAILED,
        error=ErrorEnvelope(code="stt_invoke_failed", message="boom"),
    )


def _client(monkeypatch, response: ResponseEnvelope):
    """Return an authenticated TestClient with a stubbed STT runtime."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    app = create_app()
    fake = _FakeClient(response)
    app.state.runtime_registry = _FakeRegistry(fake)
    token = loopback_token.get_or_create_loopback_token()
    return TestClient(app), {"X-Airunner-Token": token}, fake


def test_json_transcribe_frame_returns_a_transcript(
    monkeypatch, isolated_token
) -> None:
    """A base64 JSON frame is transcribed and answered with text."""
    client, headers, fake = _client(monkeypatch, _transcript())
    payload = base64.b64encode(_AUDIO).decode("ascii")
    with client.websocket_connect(_STREAM, headers=headers) as ws:
        ws.send_json(
            {"type": "transcribe", "audio": payload, "language": "en"}
        )
        reply = ws.receive_json()
    assert reply == {
        "type": "transcript",
        "text": "hello world",
        "language": "en",
        "final": True,
    }
    assert fake.envelopes[0].payload["mime_type"] == "audio/wav"


def test_binary_audio_frame_returns_a_transcript(
    monkeypatch, isolated_token
) -> None:
    """A raw binary frame is accepted as one utterance."""
    client, headers, fake = _client(monkeypatch, _transcript("raw"))
    with client.websocket_connect(_STREAM, headers=headers) as ws:
        ws.send_bytes(_AUDIO)
        reply = ws.receive_json()
    assert reply["type"] == "transcript"
    assert reply["text"] == "raw"
    assert fake.envelopes[0].payload["language"] is None


def test_failed_transcription_returns_an_error_frame(
    monkeypatch, isolated_token
) -> None:
    """A failed runtime call answers with an error frame."""
    client, headers, _ = _client(monkeypatch, _failed())
    payload = base64.b64encode(_AUDIO).decode("ascii")
    with client.websocket_connect(_STREAM, headers=headers) as ws:
        ws.send_json({"type": "transcribe", "audio": payload})
        reply = ws.receive_json()
    assert reply == {"type": "error", "message": "boom"}


def test_non_transcribe_frame_returns_an_error_frame(
    monkeypatch, isolated_token
) -> None:
    """An unrecognized frame is rejected without invoking the runtime."""
    client, headers, fake = _client(monkeypatch, _transcript())
    with client.websocket_connect(_STREAM, headers=headers) as ws:
        ws.send_json({"type": "nonsense"})
        reply = ws.receive_json()
    assert reply == {"type": "error", "message": "invalid audio frame"}
    assert fake.envelopes == []


def test_stream_socket_requires_the_loopback_token(
    monkeypatch, isolated_token
) -> None:
    """The stream socket enforces the shared loopback-token policy.

    The env is set explicitly rather than assumed: some suites in this
    repo set ``AIRUNNER_INSECURE_NO_AUTH=1`` process-wide, which would
    otherwise make this assertion pass vacuously.
    """
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    app = create_app()
    app.state.runtime_registry = None
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(_STREAM):
            pass
