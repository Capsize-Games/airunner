"""
Unit tests for ReActAgentTool in airunner.handlers.llm.agent.tools.react_agent_tool.
Covers all logic branches, including streaming, agent handling, and error/edge cases.
"""

import pytest
from unittest.mock import MagicMock, patch
from airunner.handlers.llm.agent.tools.react_agent_tool import ReActAgentTool
from airunner.handlers.llm.agent.chat_engine import ReactAgentEngine
from airunner.handlers.llm.agent.tools.chat_engine_tool import ChatEngineTool
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.tools.types import ToolOutput, ToolMetadata


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.handle_response = MagicMock()
    return agent


@pytest.fixture
def mock_chat_engine():
    engine = MagicMock()
    engine.stream_chat.return_value = MagicMock(
        response_gen=iter(["Hello, ", "world!"])
    )
    engine.chat_history = []
    return engine


# Patch: DummyReActAgentTool now provides a ToolMetadata and passes it to super().__init__
class DummyReActAgentTool(ReActAgentTool):
    def __init__(self, chat_engine, agent=None, **kwargs):
        metadata = ToolMetadata(
            name="react_agent_tool", description="desc", return_direct=False
        )
        super().__init__(
            chat_engine=chat_engine, metadata=metadata, agent=agent, **kwargs
        )

    def _get_query_str(self, *args, **kwargs):
        return kwargs.get("query", "test query")


def test_from_tools_creates_instance(monkeypatch):
    # Patch ReactAgentEngine.from_tools to return a mock
    mock_engine = MagicMock()
    monkeypatch.setattr(
        ReactAgentEngine, "from_tools", lambda *a, **k: mock_engine
    )
    tool = ReActAgentTool.from_tools(agent="agentX", return_direct=True)
    assert isinstance(tool, ReActAgentTool)
    assert tool.agent == "agentX"
    assert tool.chat_engine == mock_engine
    assert tool.metadata.name == "react_agent_tool"


def test_call_streams_and_handles_response(mock_agent, mock_chat_engine):
    tool = DummyReActAgentTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(
        query="What is the answer?", chat_history=["hi"], tool_choice="foo"
    )
    # Should call handle_response for each token
    assert mock_agent.handle_response.call_count == 2
    # Should append user and assistant messages to chat_history
    assert isinstance(mock_chat_engine.chat_history[0], ChatMessage)
    assert mock_chat_engine.chat_history[0].role == MessageRole.USER
    assert isinstance(mock_chat_engine.chat_history[1], ChatMessage)
    assert mock_chat_engine.chat_history[1].role == MessageRole.ASSISTANT
    # Should return ToolOutput with correct content
    assert isinstance(result, ToolOutput)
    assert result.content == "Hello, world!"
    assert result.tool_name == "react_agent_tool"
    assert result.raw_input["input"] == "What is the answer?"
    assert result.raw_output == "Hello, world!"


def test_call_with_empty_stream(mock_agent, mock_chat_engine):
    mock_chat_engine.stream_chat.return_value = MagicMock(
        response_gen=iter([])
    )
    tool = DummyReActAgentTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(query="", chat_history=None)
    assert result.content == ""
    assert mock_agent.handle_response.call_count == 0
    assert len(mock_chat_engine.chat_history) == 2


# Edge case: agent is None


def test_call_without_agent(mock_chat_engine):
    tool = DummyReActAgentTool(chat_engine=mock_chat_engine, agent=None)
    # Should not raise even if agent is None
    result = tool.call(query="test")
    assert result.content == "Hello, world!"
    # No handle_response calls
    # (no error should be raised)


def test_call_stream_chat_exception(mock_agent, mock_chat_engine):
    # Simulate stream_chat raising an exception
    mock_chat_engine.stream_chat.side_effect = RuntimeError("fail")
    tool = DummyReActAgentTool(chat_engine=mock_chat_engine, agent=mock_agent)
    # Should not raise, should return ToolOutput with empty content
    result = tool.call(query="fail case")
    assert isinstance(result, ToolOutput)
    assert result.content == ""
    # Should not call handle_response
    assert mock_agent.handle_response.call_count == 0
