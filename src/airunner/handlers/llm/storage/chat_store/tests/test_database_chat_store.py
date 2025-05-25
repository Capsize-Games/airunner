"""
Regression and edge-case tests for DatabaseChatStore.get_messages to ensure all returned ChatMessage objects have valid, non-None string fields and that no TypeError is raised when used in downstream templates.
"""

import pytest
from airunner.handlers.llm.storage.chat_store.database import DatabaseChatStore
from airunner.data.models import Conversation
from airunner.data.session_manager import session_scope
from llama_index.core.llms import ChatMessage


@pytest.fixture(autouse=True)
def clean_conversations():
    with session_scope() as session:
        session.query(Conversation).delete()
        session.commit()
    yield
    with session_scope() as session:
        session.query(Conversation).delete()
        session.commit()


def test_get_messages_handles_none_and_missing_fields():
    # Insert a conversation with malformed messages
    malformed_messages = [
        {"role": None, "blocks": [{"text": None}]},
        {"blocks": [{"text": "Hello"}]},
        {"role": "user", "blocks": [{}]},
        {"role": "assistant", "blocks": None},
        {"role": "user"},
        {},
    ]
    with session_scope() as session:
        conv = Conversation(key="1", value=malformed_messages)
        session.add(conv)
        session.commit()
        conv_id = conv.id
    chat_store = DatabaseChatStore()
    messages = chat_store.get_messages(str(conv_id))
    # All returned ChatMessage objects should have non-None string role and content
    for msg in messages:
        assert isinstance(msg.role, str)
        assert msg.role != ""
        assert isinstance(msg.content, str)
    # Should not raise TypeError when used in a template (simulate)
    for msg in messages:
        # Simulate Jinja2 template concatenation
        s = msg.role + ": " + msg.content
        assert isinstance(s, str)


def test_get_messages_valid_message():
    with session_scope() as session:
        conv = Conversation(
            key="2",
            value=[{"role": "user", "blocks": [{"text": "Hi there!"}]}],
        )
        session.add(conv)
        session.commit()
        conv_id = conv.id
    chat_store = DatabaseChatStore()
    messages = chat_store.get_messages(str(conv_id))
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "Hi there!"
