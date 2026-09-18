"""Tests for the chat-surface RPC paths on /api/v1/events (#2230).

Covers the logical paths the UwUChat client calls for the conversation
list, thread, session, truncate, previews, and message delete, against a
temp SQLite database. No real model, network, or live-data side effects.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.server import create_app
from airunner_services.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner_services.database import reset_engine, setup_database
from airunner_services.database.models.conversation import Conversation

_EVENTS = "/api/v1/events"


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
    db_url = f"sqlite:///{tmp_path / 'events-thread.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


def _seed_conversation() -> int:
    """Create one conversation with two raw messages."""
    manager = ConversationHistoryManager()
    session = manager.create_conversation()
    conversation_id = int(session["conversation_id"])
    manager.update_conversation_messages(
        conversation_id,
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ],
    )
    return conversation_id


def _rpc(client, method: str, path: str, body=None):
    """Open the events socket, drain bootstrap, send one rpc, read reply."""
    open_socket = client.websocket_connect
    token = loopback_token.get_or_create_loopback_token()
    with open_socket(
        _EVENTS, headers={"X-Airunner-Token": token}
    ) as ws:
        ws.receive_json()
        ws.send_json(
            {
                "type": "rpc",
                "id": "t1",
                "method": method,
                "path": path,
                "body": body or {},
            }
        )
        return ws.receive_json()


def test_thread_and_session(monkeypatch, isolated_token, test_db) -> None:
    """Thread returns a messages list; session returns a conversation id."""
    conversation_id = _seed_conversation()
    app = create_app()
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    client = TestClient(app)

    thread = _rpc(client, "GET", "/api/v1/llm/thread?chatbot_id=1")
    assert thread["status"] == 200
    assert isinstance(thread["body"]["messages"], list)

    session = _rpc(client, "GET", "/api/v1/llm/chatbot-session?chatbot_id=1")
    assert session["status"] == 200
    assert session["body"]["conversation_id"] == conversation_id


def test_truncate_keeps_tail(monkeypatch, isolated_token, test_db) -> None:
    """Truncate keeps the requested number of trailing messages."""
    conversation_id = _seed_conversation()
    app = create_app()
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    client = TestClient(app)

    result = _rpc(
        client,
        "POST",
        "/api/v1/llm/conversations/truncate",
        {"conversation_id": conversation_id, "keep_count": 1},
    )
    assert result["status"] == 200
    assert result["body"] == {"truncated": True, "kept": 1}


def test_previews_and_delete_message(
    monkeypatch, isolated_token, test_db
) -> None:
    """Previews returns a mapping; delete removes one visible message."""
    _seed_conversation()
    app = create_app()
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    client = TestClient(app)

    previews = _rpc(
        client,
        "POST",
        "/api/v1/llm/conversations/previews",
        {"chatbot_ids": []},
    )
    assert previews["status"] == 200
    assert "previews" in previews["body"]

    deleted = _rpc(client, "DELETE", "/api/v1/llm/chatbot/1/messages/0")
    assert deleted["status"] == 200
    assert "kept" in deleted["body"]


def test_create_and_delete_conversation(
    monkeypatch, isolated_token, test_db
) -> None:
    """The New and delete-conversation actions resolve, not 404."""
    app = create_app()
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    client = TestClient(app)

    created = _rpc(client, "POST", "/api/v1/llm/conversations")
    assert created["status"] == 200
    conversation_id = created["body"]["conversation_id"]

    listed = _rpc(client, "GET", "/api/v1/llm/conversations")
    assert listed["status"] == 200
    assert conversation_id in [
        row["id"] for row in listed["body"]["conversations"]
    ]

    deleted = _rpc(
        client, "DELETE", f"/api/v1/llm/conversations/{conversation_id}"
    )
    assert deleted["status"] == 200
    assert deleted["body"] == {"deleted": True}

    again = _rpc(
        client, "DELETE", f"/api/v1/llm/conversations/{conversation_id}"
    )
    assert again["status"] == 404


def test_thread_is_empty_when_conversation_query_fails(
    monkeypatch, isolated_token, test_db
) -> None:
    """A failing conversation query yields an empty thread, not a 500.

    ``filter_by`` returns ``None`` when the query raises (e.g. the
    conversation table is not present yet), which used to reach
    ``len(None)`` inside ``get_current_conversation``.
    """
    app = create_app()
    monkeypatch.setattr(server_module, "is_loopback_request", lambda c: True)
    client = TestClient(app)

    monkeypatch.setattr(
        Conversation.objects, "filter_by", lambda **kwargs: None
    )
    thread = _rpc(client, "GET", "/api/v1/llm/thread")
    assert thread["status"] == 200
    assert thread["body"]["messages"] == []
