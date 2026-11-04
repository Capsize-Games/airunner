"""API socket hardening for issues #2424-#2427.

Covers: query-string token accepted on websockets only, never plain
HTTP (F7); per-connection LLM rate-limit key under a shared loopback
credential (F8); events RPC dispatch off the event loop (F9); TTS
speed validation and serialized, time-bounded synthesis (F10).

Hermetic: stubbed runtimes, temp token store and SQLite, no binds.
"""

from __future__ import annotations

import asyncio
import base64

import pytest
from starlette.testclient import TestClient

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.routes import llm_stream_routes
from airunner_services.api.routes import tts_ws as tts_ws_module
from airunner_services.api.routes.llm_contracts import (
    WebSocketRateLimiter,
)
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database
from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    ResponseEnvelope,
    StreamDelta,
)
from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.registry import (
    RuntimeRegistry,
    RuntimeRoute,
)

_STREAM_PATH = "/api/v1/llm/stream"
_EVENTS_PATH = "/api/v1/events"
_MODELS_PATH = "/api/v1/llm/models"
_WAV_BYTES = b"RIFF____WAVEfmt "


class _FakeLLMClient:
    """Minimal double for the runtime-backed LLM client."""

    def __init__(self) -> None:
        self.calls = 0

    def stream(self, envelope):
        """Yield one final chunk per admitted message."""
        self.calls += 1
        yield StreamDelta(
            request_id=envelope.request_id,
            delta={"content": "ok"},
            final=True,
            status=EnvelopeStatus.SUCCEEDED,
        )


class _FakeTTSClient:
    """Minimal double returning a canned TTS envelope."""

    def __init__(self, response: ResponseEnvelope) -> None:
        self.response = response
        self.envelope = None

    def invoke(self, envelope):
        """Return the canned response."""
        self.envelope = envelope
        return self.response


class _FakeTTSRegistry:
    """Registry resolving one TTS client for any deployment mode."""

    def __init__(self, client: _FakeTTSClient) -> None:
        self.client = client

    def resolve(
        self, kind, provider=None, deployment_mode=None
    ):
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


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """Point the ORM at a temp SQLite file and apply the schema."""
    db_url = f"sqlite:///{tmp_path / 'release-f7-f10.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


@pytest.fixture()
def fake_llm() -> _FakeLLMClient:
    """Return a fresh fake LLM runtime client."""
    return _FakeLLMClient()


def _llm_app(monkeypatch, fake_llm, *, api_key: str = ""):
    """Return a loopback app with a fake LLM runtime registered."""
    monkeypatch.setenv("AIRUNNER_API_KEY", api_key)
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    app = create_app()
    registry = RuntimeRegistry()
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider="local"), fake_llm
    )
    app.state.runtime_registry = registry
    return app


def _huge_limiters(monkeypatch) -> None:
    """Neutralize both LLM limiters for non-rate tests."""
    monkeypatch.setattr(
        llm_stream_routes,
        "_rate_limiter",
        WebSocketRateLimiter(
            max_requests=1000, window_seconds=60.0
        ),
    )
    monkeypatch.setattr(
        llm_stream_routes,
        "_connection_rate_limiter",
        WebSocketRateLimiter(
            max_requests=1000, window_seconds=60.0
        ),
    )


def _token() -> str:
    return loopback_token.get_or_create_loopback_token()


def test_http_query_token_rejected_with_valid_secret(
    monkeypatch, isolated_token, test_db, fake_llm
) -> None:
    """A valid loopback token in ?token= must not authorize plain HTTP."""
    _huge_limiters(monkeypatch)
    app = _llm_app(monkeypatch, fake_llm)
    client = TestClient(app, raise_server_exceptions=False)
    token = _token()
    response = client.get(f"{_MODELS_PATH}?token={token}")
    assert response.status_code == 401
    root = client.get(f"/?token={token}")
    assert root.status_code == 401


def test_http_header_token_still_accepted(
    monkeypatch, isolated_token, test_db, fake_llm
) -> None:
    """The same secret in the header keeps authorizing plain HTTP."""
    _huge_limiters(monkeypatch)
    app = _llm_app(monkeypatch, fake_llm)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        _MODELS_PATH, headers={"X-Airunner-Token": _token()}
    )
    assert response.status_code not in {401, 403}


def test_second_loopback_connection_has_own_budget(
    monkeypatch, isolated_token, test_db, fake_llm
) -> None:
    """One abusive local client cannot burn every client's budget."""
    monkeypatch.setattr(
        llm_stream_routes,
        "_rate_limiter",
        WebSocketRateLimiter(
            max_requests=1000, window_seconds=60.0
        ),
    )
    monkeypatch.setattr(
        llm_stream_routes,
        "_connection_rate_limiter",
        WebSocketRateLimiter(
            max_requests=1, window_seconds=60.0
        ),
    )
    app = _llm_app(monkeypatch, fake_llm)
    client = TestClient(app)

    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as first:
        first.send_json({"message": "one"})
        assert first.receive_json()["type"] == "chunk"
        first.send_json({"message": "two"})
        response = first.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "rate_limited"

    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": _token()}
    ) as second:
        second.send_json({"message": "three"})
        assert second.receive_json()["type"] == "chunk"
    assert fake_llm.calls == 2


def test_api_key_mode_shares_credential_budget(
    monkeypatch, isolated_token, test_db, fake_llm
) -> None:
    """With API-key auth the budget key stays the credential, not conn."""
    monkeypatch.setattr(
        llm_stream_routes,
        "_connection_rate_limiter",
        WebSocketRateLimiter(
            max_requests=1000, window_seconds=60.0
        ),
    )
    app = _llm_app(monkeypatch, fake_llm, api_key="secret-key")
    client = TestClient(app)
    headers = {"X-API-Key": "secret-key"}
    with client.websocket_connect(
        _STREAM_PATH, headers=headers
    ) as first:
        first_principal = llm_stream_routes._resolve_connection_principal(
            _FakeSocket(app)
        )
        first.send_json({"message": "one"})
        assert first.receive_json()["type"] == "chunk"
    with client.websocket_connect(
        _STREAM_PATH, headers=headers
    ) as second:
        second.send_json({"message": "two"})
        assert second.receive_json()["type"] == "chunk"
    assert fake_llm.calls == 2
    assert first_principal.startswith("api_key:")


class _FakeSocket:
    """Minimal stand-in exposing the app state a principal needs."""

    def __init__(self, app) -> None:
        self.app = app


def test_connection_principal_keys(
    monkeypatch, isolated_token, test_db, fake_llm
) -> None:
    """Loopback principals differ per connection; API-key ones do not."""
    app = _llm_app(monkeypatch, fake_llm)
    first = llm_stream_routes._resolve_connection_principal(
        _FakeSocket(app)
    )
    second = llm_stream_routes._resolve_connection_principal(
        _FakeSocket(app)
    )
    assert first.startswith("conn:")
    assert first != second

    keyed = _llm_app(monkeypatch, fake_llm, api_key="secret-key")
    one = llm_stream_routes._resolve_connection_principal(
        _FakeSocket(keyed)
    )
    two = llm_stream_routes._resolve_connection_principal(
        _FakeSocket(keyed)
    )
    assert one == two
    assert one.startswith("api_key:")


def test_events_dispatch_runs_off_event_loop(
    monkeypatch, isolated_token, test_db
) -> None:
    """The RPC dispatch must not run on the server event-loop thread."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    app = create_app()
    app.state.runtime_registry = None
    token = _token()
    client = TestClient(app)

    real_to_thread = asyncio.to_thread
    calls: list[str] = []

    async def _recording_to_thread(func, /, *args, **kwargs):
        calls.append(getattr(func, "__name__", repr(func)))
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", _recording_to_thread)
    with client.websocket_connect(
        _EVENTS_PATH, headers={"X-Airunner-Token": token}
    ) as ws:
        assert ws.receive_json()["type"] == "bootstrap"
        ws.send_json(
            {
                "type": "rpc",
                "id": "r1",
                "method": "GET",
                "path": "/api/v1/health",
                "body": {},
            }
        )
        response = ws.receive_json()
        assert response["type"] == "rpc_response"
        assert response["status"] == 200
    assert "dispatch" in calls


def _tts_client(monkeypatch, response: ResponseEnvelope):
    """Return an authenticated TTS TestClient with a stubbed runtime."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    app = create_app()
    fake = _FakeTTSClient(response)
    app.state.runtime_registry = _FakeTTSRegistry(fake)
    token = _token()
    return TestClient(app), {"X-Airunner-Token": token}, fake


def _succeeded() -> ResponseEnvelope:
    return ResponseEnvelope(
        request_id="r1",
        status=EnvelopeStatus.SUCCEEDED,
        payload={
            "audio_b64": base64.b64encode(_WAV_BYTES).decode("ascii")
        },
    )


def test_tts_invalid_speed_keeps_connection_open(
    monkeypatch, isolated_token
) -> None:
    """An unparseable speed answers invalid_speed, not a dropped socket."""
    client, headers, _ = _tts_client(monkeypatch, _succeeded())
    with client.websocket_connect(
        "/api/v1/tts/ws", headers=headers
    ) as ws:
        ws.send_json(
            {"type": "synthesize", "text": "hello", "speed": "fast"}
        )
        reply = ws.receive_json()
        assert reply == {"type": "error", "message": "invalid_speed"}
        ws.send_json({"type": "synthesize", "text": "hello"})
        assert ws.receive_json()["type"] == "audio"


def test_tts_out_of_range_speed_rejected(
    monkeypatch, isolated_token
) -> None:
    """Speeds outside 0.25-4.0 are rejected before the runtime runs."""
    client, headers, fake = _tts_client(monkeypatch, _succeeded())
    with client.websocket_connect(
        "/api/v1/tts/ws", headers=headers
    ) as ws:
        ws.send_json(
            {"type": "synthesize", "text": "hello", "speed": 99.0}
        )
        assert ws.receive_json() == {
            "type": "error",
            "message": "invalid_speed",
        }
    assert fake.envelope is None


def _direct_ws(app):
    """Return a minimal async fake socket bound to a fake registry."""

    class _Direct:
        def __init__(self) -> None:
            self.sent: list[dict] = []
            self.app = app

        async def send_json(self, payload: dict) -> None:
            self.sent.append(payload)

    return _Direct()


def test_direct_synthesize_timeout_frame(
    monkeypatch, isolated_token
) -> None:
    """_synthesize with a tiny bound reports synthesis_timeout."""
    import time as _time

    class _HangingClient(_FakeTTSClient):
        def invoke(self, envelope):
            _time.sleep(5)
            return self.response

    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    app = create_app()
    hanging = _HangingClient(
        ResponseEnvelope(
            request_id="r1",
            status=EnvelopeStatus.FAILED,
            error=ErrorEnvelope(code="boom", message="boom"),
        )
    )
    app.state.runtime_registry = _FakeTTSRegistry(hanging)
    ws = _direct_ws(app)

    async def _run() -> None:
        await tts_ws_module._synthesize(
            ws,
            {"type": "synthesize", "text": "hello"},
            asyncio.Lock(),
            timeout=0.05,
        )

    asyncio.run(_run())
    assert ws.sent == [
        {"type": "error", "message": "synthesis_timeout"}
    ]


def test_direct_synthesizes_serialize_per_connection(
    monkeypatch, isolated_token
) -> None:
    """Two concurrent synthesizes on one lock never overlap."""
    import threading as _threading
    import time as _time

    active = 0
    peak = 0
    peak_lock = _threading.Lock()

    class _SlowClient(_FakeTTSClient):
        def invoke(self, envelope):
            nonlocal active, peak
            with peak_lock:
                active += 1
                peak = max(peak, active)
            try:
                _time.sleep(0.2)
                return self.response
            finally:
                with peak_lock:
                    active -= 1

    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    app = create_app()
    slow = _SlowClient(_succeeded())
    app.state.runtime_registry = _FakeTTSRegistry(slow)

    async def _run() -> list:
        first = _direct_ws(app)
        second = _direct_ws(app)
        lock = asyncio.Lock()
        await asyncio.gather(
            tts_ws_module._synthesize(
                first, {"type": "synthesize", "text": "one"}, lock
            ),
            tts_ws_module._synthesize(
                second, {"type": "synthesize", "text": "two"}, lock
            ),
        )
        return [first.sent, second.sent]

    sent = asyncio.run(_run())
    assert peak == 1
    assert [frame["type"] for frames in sent for frame in frames] == [
        "audio",
        "audio",
    ]
