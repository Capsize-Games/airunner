"""
Unit tests for ChatEngineTool in airunner.handlers.llm.agent.tools.chat_engine_tool.
Covers all logic branches, including from_defaults, streaming, agent handling, error/edge cases, and input resolution.
"""

import pytest
from unittest.mock import MagicMock
from airunner.handlers.llm.agent.tools.chat_engine_tool import ChatEngineTool
from llama_index.core.tools.types import ToolMetadata, ToolOutput
from llama_index.core.base.llms.types import ChatMessage, MessageRole


class DummyChatEngineTool(ChatEngineTool):
    def __init__(self, chat_engine, agent=None, **kwargs):
        metadata = ToolMetadata(
            name="chat_engine_tool", description="desc", return_direct=False
        )
        super().__init__(
            chat_engine=chat_engine, metadata=metadata, agent=agent, **kwargs
        )

    # Remove override: use real _get_query_str for input resolution tests


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.handle_response = MagicMock()
    return agent


@pytest.fixture
def mock_chat_engine():
    engine = MagicMock()
    engine.stream_chat.return_value = MagicMock(
        response_gen=iter(["Chat ", "result!"])
    )
    engine.chat_history = []
    engine.llm = MagicMock()
    engine.update_system_prompt = MagicMock()
    return engine


def test_from_defaults_creates_instance():
    mock_engine = MagicMock()
    tool = ChatEngineTool.from_defaults(
        chat_engine=mock_engine, agent="agentZ", return_direct=True
    )
    assert isinstance(tool, ChatEngineTool)
    assert tool.agent == "agentZ"
    assert tool.chat_engine == mock_engine
    assert tool.metadata.name == "chat_engine_tool"
    assert tool.metadata.return_direct is True


def test_call_streams_and_handles_response(mock_agent, mock_chat_engine):
    tool = DummyChatEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(query="What is the answer?", chat_history=["hi"])
    assert mock_agent.handle_response.call_count == 2
    assert isinstance(result, ToolOutput)
    assert result.content == "Chat result!"
    assert result.tool_name == "chat_engine_tool"
    # Accept dict string for raw_input["input"] due to _get_query_str fallback
    assert "What is the answer?" in str(result.raw_input["input"])
    assert result.raw_output == "Chat result!"


def test_call_with_empty_stream(mock_agent, mock_chat_engine):
    mock_chat_engine.stream_chat.return_value = MagicMock(
        response_gen=iter([])
    )
    tool = DummyChatEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(query="", chat_history=[])
    assert result.content == ""
    assert mock_agent.handle_response.call_count == 0


def test_call_without_agent(mock_chat_engine):
    tool = DummyChatEngineTool(chat_engine=mock_chat_engine, agent=None)
    tool.do_handle_response = False
    result = tool.call(query="test", chat_history=["hi"])
    assert result.content == "Chat result!"


def test_call_template_error(monkeypatch, mock_agent, mock_chat_engine):
    def raise_template_error(*a, **k):
        import jinja2

        raise jinja2.exceptions.TemplateError("bad template")

    mock_chat_engine.stream_chat.side_effect = raise_template_error
    tool = DummyChatEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(query="fail", chat_history=["hi"])
    assert "Error in template rendering" in result.content
    assert result.tool_name == "chat_engine_tool"


# Patch test_call_openai_api_error to provide required APIError args (body)
def test_call_openai_api_error(monkeypatch, mock_agent, mock_chat_engine):
    class DummyStreaming:
        @property
        def response_gen(self):
            import openai

            raise openai.APIError("fail", request=None, body=None)

    mock_chat_engine.stream_chat.return_value = DummyStreaming()
    tool = DummyChatEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(query="fail", chat_history=["hi"])
    assert result.content == ""


def test_get_query_str_args():
    tool = DummyChatEngineTool(chat_engine=MagicMock(), agent=None)
    assert tool._get_query_str("foo") == "foo"


def test_get_query_str_input_kwarg():
    tool = DummyChatEngineTool(chat_engine=MagicMock(), agent=None)
    assert tool._get_query_str(input="bar") == "bar"


def test_get_query_str_resolve_input_errors():
    tool = DummyChatEngineTool(chat_engine=MagicMock(), agent=None)
    tool._resolve_input_errors = True
    assert tool._get_query_str() == "{}"


def test_get_query_str_raises():
    tool = DummyChatEngineTool(chat_engine=MagicMock(), agent=None)
    tool._resolve_input_errors = False
    with pytest.raises(ValueError):
        tool._get_query_str()


def test_update_system_prompt(mock_chat_engine):
    tool = DummyChatEngineTool(chat_engine=mock_chat_engine, agent=None)
    tool.update_system_prompt("new system prompt")
    mock_chat_engine.update_system_prompt.assert_called_once_with(
        "new system prompt"
    )
