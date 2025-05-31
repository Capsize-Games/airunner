"""
Tests for BaseConversationEngine and unified message/memory handling.
"""

import pytest
import datetime
from unittest.mock import MagicMock
from airunner.handlers.llm.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)


class DummyAgent:
    def __init__(self):
        self.username = "test_user"
        self.botname = "test_bot"
        self.logger = MagicMock()
        self.conversation_id = 1
        self._sync_memory_to_all_engines = MagicMock()
        self.chat_memory = MagicMock()
        self._make_chat_message = lambda role, content: MagicMock(
            role=role, blocks=[MagicMock(text=content)]
        )


class DummyConversation:
    def __init__(self):
        self.value = []


class DummyConversationModel:
    objects = MagicMock()


@pytest.fixture
def agent():
    return DummyAgent()


@pytest.fixture
def conversation():
    return DummyConversation()


@pytest.fixture(autouse=True)
def patch_conversation_model(monkeypatch):
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.engines.base_conversation_engine.Conversation",
        DummyConversationModel,
    )


class TestBaseConversationEngine:
    def test_append_conversation_messages(self, agent, conversation):
        engine = BaseConversationEngine(agent)
        engine.append_conversation_messages(conversation, "hello", "hi there")
        assert len(conversation.value) == 2
        assert conversation.value[0]["role"] == "user"
        assert conversation.value[0]["content"] == "hello"
        assert conversation.value[1]["role"] == "assistant"
        assert conversation.value[1]["content"] == "hi there"

    def test_append_conversation_messages_no_assistant(
        self, agent, conversation
    ):
        engine = BaseConversationEngine(agent)
        engine.append_conversation_messages(conversation, "hello", None)
        assert len(conversation.value) == 1
        assert conversation.value[0]["role"] == "user"
        assert conversation.value[0]["content"] == "hello"

    def test_update_conversation_state(self, agent, conversation):
        engine = BaseConversationEngine(agent)
        conversation.value = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        engine.update_conversation_state(conversation)
        # Should call Conversation.objects.update
        DummyConversationModel.objects.update.assert_called_once()
        # Should call chat_memory.set
        agent.chat_memory.set.assert_called_once()
        # Should call _sync_memory_to_all_engines
        agent._sync_memory_to_all_engines.assert_called_once()
