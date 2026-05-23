"""Tests for conversation session service routes."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


def _request(worker=None):
    """Build a minimal request double for direct route calls."""
    lifecycle_service = SimpleNamespace(
        sync_selected_conversation=lambda _conversation_id: None,
        sync_deleted_conversation=lambda _conversation_id: None,
    )
    if worker is not None:
        lifecycle_service = SimpleNamespace(
            sync_selected_conversation=lambda conversation_id: worker.on_llm_load_conversation(
                {"conversation_id": conversation_id}
            ),
            sync_deleted_conversation=lambda conversation_id: worker.on_conversation_deleted_signal(
                {"conversation_id": conversation_id}
            ),
        )
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                lifecycle_service=lifecycle_service
            )
        )
    )


def test_list_conversations_returns_service_metadata(monkeypatch):
    from airunner_api.routes import conversations as module

    manager = SimpleNamespace(
        list_conversations=lambda limit: [{"id": 7, "title": "Conversation"}]
    )
    monkeypatch.setattr(module, "ConversationHistoryManager", lambda: manager)

    response = asyncio.run(module.list_conversations(limit=25))

    assert response.conversations[0].id == 7
    assert response.conversations[0].title == "Conversation"


def test_select_conversation_syncs_worker_state(monkeypatch):
    from airunner_api.routes import conversations as module

    manager = SimpleNamespace(
        get_conversation_session=lambda **_kwargs: {
            "conversation_id": 7,
            "conversation": {"id": 7, "user_data": {}},
            "messages": [{"content": "hello", "is_bot": False}],
        }
    )
    worker = SimpleNamespace(on_llm_load_conversation=lambda data: calls.append(data))
    calls = []
    monkeypatch.setattr(module, "ConversationHistoryManager", lambda: manager)

    response = asyncio.run(
        module.select_conversation(
            module.SelectConversationRequest(conversation_id=7, max_messages=50),
            _request(worker),
        )
    )

    assert response.conversation_id == 7
    assert calls == [{"conversation_id": 7}]


def test_delete_conversation_notifies_worker(monkeypatch):
    from airunner_api.routes import conversations as module

    manager = SimpleNamespace(delete_conversation=lambda _conversation_id: True)
    calls = []
    worker = SimpleNamespace(
        on_conversation_deleted_signal=lambda data: calls.append(data)
    )
    monkeypatch.setattr(module, "ConversationHistoryManager", lambda: manager)

    response = asyncio.run(module.delete_conversation(7, _request(worker)))

    assert response.deleted is True
    assert calls == [{"conversation_id": 7}]


def test_select_conversation_raises_for_missing_conversation(monkeypatch):
    from airunner_api.routes import conversations as module

    manager = SimpleNamespace(
        get_conversation_session=lambda **_kwargs: {
            "conversation": None,
            "conversation_id": None,
            "messages": [],
        }
    )
    monkeypatch.setattr(module, "ConversationHistoryManager", lambda: manager)

    with pytest.raises(HTTPException):
        asyncio.run(
            module.select_conversation(
                module.SelectConversationRequest(conversation_id=7),
                _request(),
            )
        )
