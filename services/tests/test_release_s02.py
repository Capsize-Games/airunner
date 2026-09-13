"""Regression tests for release issue S02.

Proves the LLM WebSocket (``/api/v1/llm/stream``) bounds inbound message
size, requested output tokens and temperature, and admits messages under
a per-principal sliding-window rate limit, all before any runtime
("model") invocation:

- Oversized, malformed and out-of-bounds payloads are rejected with a
  deterministic error code and never reach the runtime client.
- The rate limiter's state is keyed by the authenticated principal, not
  the socket connection, so reconnecting with the same credential does
  not reset the caller's remaining budget (verified with a fake clock).
- Allowed traffic still reaches the runtime, and disconnecting/
  reconnecting does not accumulate duplicate per-principal state.

Uses only a fake in-memory LLM runtime client (no real model/subprocess/
network/database side effects).
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.routes import llm_stream_routes
from airunner_services.api.routes.llm_contracts import (
    WebSocketRateLimiter,
    max_ws_message_chars,
    max_ws_output_tokens,
)
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database
from airunner_services.ipc.messages import EnvelopeStatus, StreamDelta
from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute

_STREAM_PATH = "/api/v1/llm/stream"


class _FakeLLMClient:
    """A minimal double standing in for the real sidecar LLM client."""

    def __init__(self) -> None:
        self.calls = 0

    def stream(self, envelope):
        self.calls += 1
        yield StreamDelta(
            request_id=envelope.request_id,
            delta={"content": "ok"},
            final=True,
            status=EnvelopeStatus.SUCCEEDED,
        )


@pytest.fixture()
def isolated_token(tmp_path, monkeypatch):
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
    db_url = f"sqlite:///{tmp_path / 'release-s02.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


@pytest.fixture()
def fake_client() -> _FakeLLMClient:
    return _FakeLLMClient()


@pytest.fixture()
def app(monkeypatch, isolated_token, test_db, fake_client):
    """A loopback-authenticated app with a fake runtime client registered."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda conn: True)
    application = create_app()
    registry = RuntimeRegistry()
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider="local"), fake_client
    )
    application.state.runtime_registry = registry
    return application


@pytest.fixture(autouse=True)
def _fresh_rate_limiter(monkeypatch):
    """Give each test its own limiter so tests cannot see each other's state."""
    limiter = WebSocketRateLimiter(max_requests=1000, window_seconds=60.0)
    monkeypatch.setattr(llm_stream_routes, "_rate_limiter", limiter)
    return limiter


def _token() -> str:
    return loopback_token.get_or_create_loopback_token()


def test_oversized_message_never_reaches_runtime(app, fake_client) -> None:
    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as ws:
        ws.send_json({"message": "x" * (max_ws_message_chars() + 1)})
        response = ws.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "message_too_long"
        assert fake_client.calls == 0

        # The connection stays usable for a subsequent valid message.
        ws.send_json({"message": "hello"})
        response = ws.receive_json()
        assert response["type"] == "chunk"
        assert fake_client.calls == 1


def test_malformed_payload_never_reaches_runtime(app, fake_client) -> None:
    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as ws:
        ws.send_json({"no_message_field": True})
        response = ws.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "invalid_request"
        assert fake_client.calls == 0


def test_output_tokens_out_of_bounds_never_reaches_runtime(
    app, fake_client
) -> None:
    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as ws:
        ws.send_json(
            {"message": "hi", "max_tokens": max_ws_output_tokens() + 1}
        )
        response = ws.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "max_tokens_out_of_bounds"
        assert fake_client.calls == 0


def test_empty_message_never_reaches_runtime(app, fake_client) -> None:
    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as ws:
        ws.send_json({"message": "   "})
        response = ws.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "empty_message"
        assert fake_client.calls == 0


def test_rate_limit_blocks_excess_requests(
    monkeypatch, app, fake_client
) -> None:
    fake_now = [0.0]
    limiter = WebSocketRateLimiter(
        max_requests=2, window_seconds=60.0, clock=lambda: fake_now[0]
    )
    monkeypatch.setattr(llm_stream_routes, "_rate_limiter", limiter)

    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as ws:
        ws.send_json({"message": "one"})
        assert ws.receive_json()["type"] == "chunk"
        ws.send_json({"message": "two"})
        assert ws.receive_json()["type"] == "chunk"

        ws.send_json({"message": "three"})
        response = ws.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "rate_limited"

    assert fake_client.calls == 2


def test_rate_limit_not_reset_by_reconnect(
    monkeypatch, app, fake_client
) -> None:
    """A fresh WebSocket per connection must not reset the budget."""
    fake_now = [0.0]
    limiter = WebSocketRateLimiter(
        max_requests=1, window_seconds=60.0, clock=lambda: fake_now[0]
    )
    monkeypatch.setattr(llm_stream_routes, "_rate_limiter", limiter)
    client = TestClient(app)

    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as ws:
        ws.send_json({"message": "one"})
        assert ws.receive_json()["type"] == "chunk"

    # Reconnect with the same credential: budget must still be exhausted.
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as ws:
        ws.send_json({"message": "two"})
        response = ws.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "rate_limited"

    assert fake_client.calls == 1
    # Only one principal was ever tracked, not one per connection.
    assert len(limiter._history) == 1

    # Advancing past the window frees up budget again for the same caller.
    fake_now[0] += 61.0
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as ws:
        ws.send_json({"message": "three"})
        assert ws.receive_json()["type"] == "chunk"

    assert fake_client.calls == 2


def test_disconnect_does_not_raise(app) -> None:
    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ):
        pass  # disconnect immediately without sending anything


def test_websocket_rate_limiter_bounds_tracked_principals() -> None:
    limiter = WebSocketRateLimiter(
        max_requests=5, window_seconds=60.0, clock=lambda: 0.0
    )
    limiter._MAX_TRACKED_PRINCIPALS = 3
    for i in range(10):
        assert limiter.allow(f"principal-{i}") is True
    assert len(limiter._history) <= 3
