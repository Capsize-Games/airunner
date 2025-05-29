"""
Tests for SearchEngineTool: context-aware, multi-turn conversational search.
"""

import pytest
from unittest.mock import MagicMock, patch
from airunner.handlers.llm.agent.tools.search_engine_tool import (
    SearchEngineTool,
)
from airunner.handlers.llm.agent.memory.chat_memory_buffer import (
    ChatMemoryBuffer,
)
from llama_index.core.tools.types import ToolMetadata
from llama_index.core.base.llms.types import ChatMessage, MessageRole


class DummyLLM:
    class metadata:
        context_window = 2048
        system_role = "system"

    def __init__(self):
        self.llm_request = None


class DummyAgent:
    def __init__(self):
        self.chat_memory = ChatMemoryBuffer.from_defaults(
            token_limit=100, chat_store=None, chat_store_key="1"
        )


@pytest.fixture
def dummy_llm():
    return DummyLLM()


@pytest.fixture
def dummy_agent():
    return DummyAgent()


@pytest.fixture
def tool(dummy_llm, dummy_agent):
    metadata = ToolMetadata(
        name="search_engine_tool", description="desc", return_direct=True
    )
    return SearchEngineTool(
        llm=dummy_llm, metadata=metadata, agent=dummy_agent
    )


@patch(
    "airunner.handlers.llm.agent.tools.search_engine_tool.AggregatedSearchTool.aggregated_search_sync"
)
@patch(
    "airunner.handlers.llm.agent.tools.search_engine_tool.RefreshSimpleChatEngine.stream_chat"
)
def test_contextual_search_adds_to_memory(
    mock_stream_chat, mock_agg_search, tool, dummy_agent
):
    # Simulate search results
    mock_agg_search.return_value = {
        "google": [{"title": "A", "snippet": "foo", "link": "l1"}]
    }

    # Simulate streaming LLM response
    class DummyStream:
        response_gen = iter(["This is a summary."])

    mock_stream_chat.return_value = DummyStream()

    # Initial chat memory should be empty
    assert dummy_agent.chat_memory.get() == []
    # Call tool with a query
    result = tool.call(input="What is foo?", chat_history=None)
    assert "summary" in result.content
    # Chat memory should now have user and assistant messages
    messages = dummy_agent.chat_memory.get()
    assert len(messages) == 2
    assert messages[0].role == MessageRole.USER
    assert "What is foo?" in messages[0].content
    assert messages[1].role == MessageRole.ASSISTANT
    assert "summary" in messages[1].content


@patch(
    "airunner.handlers.llm.agent.tools.search_engine_tool.AggregatedSearchTool.aggregated_search_sync"
)
@patch(
    "airunner.handlers.llm.agent.tools.search_engine_tool.RefreshSimpleChatEngine.stream_chat"
)
def test_followup_query_uses_context(
    mock_stream_chat, mock_agg_search, tool, dummy_agent
):
    # Simulate search results
    mock_agg_search.return_value = {
        "google": [{"title": "A", "snippet": "foo", "link": "l1"}]
    }

    # Simulate streaming LLM response
    class DummyStream:
        response_gen = iter(["First answer."])

    mock_stream_chat.return_value = DummyStream()
    # First turn
    tool.call(input="What is foo?", chat_history=None)

    # Second turn: follow-up
    class DummyStream2:
        response_gen = iter(["Follow-up answer."])

    mock_stream_chat.return_value = DummyStream2()
    result = tool.call(input="And what about bar?", chat_history=None)
    # The chat memory should now have 4 messages (2 turns)
    messages = dummy_agent.chat_memory.get()
    assert len(messages) == 4
    assert messages[-2].role == MessageRole.USER
    assert "bar" in messages[-2].content
    assert messages[-1].role == MessageRole.ASSISTANT
    assert "Follow-up" in messages[-1].content
