"""Regression tests for release issue S01.

Proves the LLM WebSocket (``/api/v1/llm/stream``) enforces the same
API-key/loopback-token policy as the HTTP API, and rejects unapproved
browser Origins, before ``accept()`` or any runtime resolution:

- An API key configured for HTTP also blocks unauthenticated sockets.
- Missing/wrong loopback credentials and unrelated Origins never resolve
  the runtime (the socket is closed with WS_1008_POLICY_VIOLATION before
  ``accept()``).
- Valid native (no Origin header) and configured-browser (allowlisted
  Origin) clients are accepted, using a stubbed runtime registry so no
  real model/subprocess is ever started.
- The unrelated ``/api/v1/health`` HTTP behavior is unchanged.

Uses only doubles for the runtime boundary (``app.state.runtime_registry``
is stubbed to ``None``); no real model, network, or persistent database
side effects.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database

_STREAM_PATH = "/api/v1/llm/stream"
_HEALTH_PATH = "/api/v1/health"
_POLICY_VIOLATION = 1008


@pytest.fixture()
def isolated_token(tmp_path, monkeypatch):
    """Point the token store at a temp path and reset its module cache."""
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
    """Point the ORM at a temp SQLite file (mirrors test_loopback_auth.py)."""
    db_url = f"sqlite:///{tmp_path / 'release-s01.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


def _build_app(monkeypatch, *, api_key: str = "", insecure_no_auth: bool = False):
    """Create an app with a stubbed runtime registry (no real sidecar)."""
    monkeypatch.setenv("AIRUNNER_API_KEY", api_key)
    monkeypatch.setenv(
        "AIRUNNER_INSECURE_NO_AUTH", "1" if insecure_no_auth else "0"
    )
    app = create_app()
    # Fake the runtime boundary: require_websocket_runtime_registry() raises
    # a clean 503 instead of a real sidecar client ever being resolved.
    app.state.runtime_registry = None
    return app


def _request(app, method: str, path: str) -> httpx.Response:
    """Issue one loopback-looking plain HTTP request against the ASGI app."""
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 55555))

    async def _run() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:55555", timeout=10.0
        ) as client:
            return await client.request(method, path)

    return asyncio.run(_run())


def test_health_endpoint_unaffected(monkeypatch, isolated_token, test_db) -> None:
    """The refactor into authenticate_connection() must not change /health."""
    app = _build_app(monkeypatch)
    response = _request(app, "GET", _HEALTH_PATH)
    assert response.status_code == 200


def test_websocket_rejected_without_any_auth(
    monkeypatch, isolated_token, test_db
) -> None:
    """No API key, no insecure bypass, non-loopback caller (TestClient
    default): the socket must be refused before accept()."""
    app = _build_app(monkeypatch)
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(_STREAM_PATH):
            pass
    assert exc_info.value.code == _POLICY_VIOLATION


def test_websocket_rejected_with_wrong_loopback_token(
    monkeypatch, isolated_token, test_db
) -> None:
    app = _build_app(monkeypatch)
    monkeypatch.setattr(server_module, "is_loopback_request", lambda conn: True)
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            _STREAM_PATH, headers={"X-Airunner-Token": "definitely-wrong"}
        ):
            pass
    assert exc_info.value.code == _POLICY_VIOLATION


def test_websocket_rejected_with_unrelated_origin(
    monkeypatch, isolated_token, test_db
) -> None:
    """A valid loopback token does not excuse an unapproved browser Origin."""
    app = _build_app(monkeypatch)
    monkeypatch.setattr(server_module, "is_loopback_request", lambda conn: True)
    token = loopback_token.get_or_create_loopback_token()
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            _STREAM_PATH,
            headers={
                "X-Airunner-Token": token,
                "Origin": "http://evil.example",
            },
        ):
            pass
    assert exc_info.value.code == _POLICY_VIOLATION


def test_websocket_accepts_native_client_with_valid_loopback_token(
    monkeypatch, isolated_token, test_db
) -> None:
    """A native client (no Origin header) with a valid loopback token."""
    app = _build_app(monkeypatch)
    monkeypatch.setattr(server_module, "is_loopback_request", lambda conn: True)
    token = loopback_token.get_or_create_loopback_token()
    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-Airunner-Token": token}
    ) as ws:
        assert ws is not None


def test_websocket_accepts_browser_client_with_allowed_origin(
    monkeypatch, isolated_token, test_db
) -> None:
    app = _build_app(monkeypatch)
    monkeypatch.setattr(server_module, "is_loopback_request", lambda conn: True)
    token = loopback_token.get_or_create_loopback_token()
    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH,
        headers={
            "X-Airunner-Token": token,
            "Origin": "http://localhost:5173",
        },
    ) as ws:
        assert ws is not None


def test_websocket_api_key_mode_blocks_without_key(
    monkeypatch, isolated_token, test_db
) -> None:
    """An API key configured for HTTP also blocks unauthenticated sockets."""
    app = _build_app(monkeypatch, api_key="secret-key-123")
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(_STREAM_PATH):
            pass
    assert exc_info.value.code == _POLICY_VIOLATION


def test_websocket_api_key_mode_allows_with_key(
    monkeypatch, isolated_token, test_db
) -> None:
    app = _build_app(monkeypatch, api_key="secret-key-123")
    client = TestClient(app)
    with client.websocket_connect(
        _STREAM_PATH, headers={"X-API-Key": "secret-key-123"}
    ) as ws:
        assert ws is not None


def test_websocket_insecure_no_auth_bypasses(
    monkeypatch, isolated_token, test_db
) -> None:
    app = _build_app(monkeypatch, insecure_no_auth=True)
    client = TestClient(app)
    with client.websocket_connect(_STREAM_PATH) as ws:
        assert ws is not None
