"""
Tests for BaseAgent conversation and memory integration with unified engine logic.
"""

import pytest
from unittest.mock import MagicMock, patch
from airunner.handlers.llm.agent.agents.base import BaseAgent
from airunner.handlers.llm.agent.chat_engine import RefreshSimpleChatEngine
from airunner.handlers.llm.agent.tools.chat_engine_tool import ChatEngineTool
from airunner.handlers.llm.agent.tools.search_engine_tool import (
    SearchEngineTool,
)
from airunner.handlers.llm.agent.tools.rag_engine_tool import RAGEngineTool
from airunner.handlers.llm.agent.tools.react_agent_tool import ReActAgentTool


class DummyConversation:
    def __init__(self):
        self.value = []


class DummyUser:
    username = "test_user"
    zipcode = "00000"
    location_display_name = "Testville"


class DummyChatbot:
    botname = "test_bot"
    bot_personality = "friendly"
    use_mood = False
    use_personality = False
    use_datetime = False


@pytest.fixture
def agent(monkeypatch):
    class DummyAgent(BaseAgent):
        def __init__(self):
            super().__init__()
            self.user = DummyUser()
            self.chatbot = DummyChatbot()
            self.logger = MagicMock()
            self.conversation = DummyConversation()
            self.conversation_id = 1
            self.chat_memory = MagicMock()
            self._sync_memory_to_all_engines = MagicMock()
            self._make_chat_message = lambda role, content: MagicMock(
                role=role, blocks=[MagicMock(text=content)]
            )

    return DummyAgent()


@pytest.mark.parametrize(
    "engine_cls",
    [
        RefreshSimpleChatEngine,
        ChatEngineTool,
        SearchEngineTool,
        RAGEngineTool,
        ReActAgentTool,
    ],
)
def test_engine_appends_and_updates(agent, engine_cls):
    engine = engine_cls(agent)
    conversation = agent.conversation
    # Test append
    engine.append_conversation_messages(
        conversation, "user msg", "assistant msg"
    )
    assert conversation.value[-2]["content"] == "user msg"
    assert conversation.value[-1]["content"] == "assistant msg"
    # Test update
    with patch.object(engine, "agent", agent):
        engine.update_conversation_state(conversation)
        agent.chat_memory.set.assert_called()
        agent._sync_memory_to_all_engines.assert_called()
