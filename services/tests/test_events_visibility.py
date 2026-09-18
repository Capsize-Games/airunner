"""Data-visibility regression test for the events surface (#2230, B3f).

A conversation row written before the UwUChat surface existed — i.e. by
the old widget's data layer — must stay visible through the new logical
routes. This is a read-in-place guarantee (design-note decision 4): no
migration, no rewrite, no schema change.

Uses a temp SQLite database and a temp loopback token; the runtime
registry is stubbed out, so no model or network is touched.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database
from airunner_services.database.models.conversation import Conversation

_EVENTS = "/api/v1/events"


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
    db_url = f"sqlite:///{tmp_path / 'visibility.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


def _open_socket(monkeypatch):
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    app = create_app()
    app.state.runtime_registry = None
    token = loopback_token.get_or_create_loopback_token()
    client = TestClient(app)
    return client, {"X-Airunner-Token": token}


def _rpc(ws, request_id: str, method: str, path: str):
    ws.send_json(
        {
            "type": "rpc",
            "id": request_id,
            "method": method,
            "path": path,
            "body": {},
        }
    )
    return ws.receive_json()


def test_pre_existing_conversation_is_visible(
    monkeypatch, isolated_token, test_db
) -> None:
    """A row created outside the new routes still lists through them."""
    legacy = Conversation.objects.create(
        title="Thread from the old widget",
        summary="Pre-existing summary",
        value=[{"name": "User", "content": "before", "is_bot": False}],
    )
    assert legacy is not None and legacy.id is not None

    client, headers = _open_socket(monkeypatch)
    with client.websocket_connect(_EVENTS, headers=headers) as ws:
        assert ws.receive_json()["type"] == "bootstrap"
        resp = _rpc(ws, "c1", "GET", "/api/v1/llm/conversations")

    assert resp["type"] == "rpc_response"
    assert resp["status"] == 200
    rows = resp["body"]["conversations"]
    match = [row for row in rows if row["id"] == legacy.id]
    assert match, rows
    assert match[0]["title"] == "Thread from the old widget"
    assert match[0]["summary"] == "Pre-existing summary"
    assert match[0]["message_count"] == 1
