"""Tests for the UwUChat-compatible events socket (#2230).

Proves ``/api/v1/events`` pushes the bootstrap frame, answers allowlisted
``rpc`` frames in the client's envelope, rejects unknown logical paths,
and enforces the same API-key/loopback-token policy as the HTTP API —
including the query-string token a browser WebSocket must use.

Uses a temp SQLite database and a temp loopback token; no real model,
network, or live-data side effects.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database

_EVENTS = "/api/v1/events"
_POLICY_VIOLATION = 1008


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
    db_url = f"sqlite:///{tmp_path / 'events.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


def _app(monkeypatch, *, insecure: bool = False):
    """Create an app whose runtime registry is stubbed out."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv(
        "AIRUNNER_INSECURE_NO_AUTH", "1" if insecure else "0"
    )
    app = create_app()
    app.state.runtime_registry = None
    return app


def test_events_rejects_without_credentials(
    monkeypatch, isolated_token, test_db
) -> None:
    """No token, non-loopback caller: refused before accept()."""
    app = _app(monkeypatch)
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(_EVENTS):
            pass
    assert exc.value.code == _POLICY_VIOLATION


def test_events_bootstrap_and_health_rpc(
    monkeypatch, isolated_token, test_db
) -> None:
    """A valid loopback token gets bootstrap, then an rpc_response."""
    app = _app(monkeypatch)
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    token = loopback_token.get_or_create_loopback_token()
    client = TestClient(app)
    with client.websocket_connect(
        _EVENTS, headers={"X-Airunner-Token": token}
    ) as ws:
        first = ws.receive_json()
        assert first["type"] == "bootstrap"
        assert "chatbots" in first["body"]
        ws.send_json(
            {
                "type": "rpc",
                "id": "r1",
                "method": "GET",
                "path": "/api/v1/health",
                "body": {},
            }
        )
        resp = ws.receive_json()
        assert resp["type"] == "rpc_response"
        assert resp["id"] == "r1"
        assert resp["status"] == 200
        assert resp["body"] == {"status": "ok"}


def test_events_accepts_query_string_token(
    monkeypatch, isolated_token, test_db
) -> None:
    """A browser WebSocket sends the token in ?token=, not a header."""
    app = _app(monkeypatch)
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    token = loopback_token.get_or_create_loopback_token()
    client = TestClient(app)
    with client.websocket_connect(
        f"{_EVENTS}?token={token}"
    ) as ws:
        assert ws.receive_json()["type"] == "bootstrap"


def test_events_unknown_path_returns_404(
    monkeypatch, isolated_token, test_db
) -> None:
    """An unlisted logical path is refused, not guessed at."""
    app = _app(monkeypatch)
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    token = loopback_token.get_or_create_loopback_token()
    client = TestClient(app)
    with client.websocket_connect(
        _EVENTS, headers={"X-Airunner-Token": token}
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "type": "rpc",
                "id": "r2",
                "method": "GET",
                "path": "/api/v1/does-not-exist",
                "body": {},
            }
        )
        resp = ws.receive_json()
        assert resp["status"] == 404
        assert resp["id"] == "r2"
