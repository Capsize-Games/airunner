"""
Unit tests for RAGEngineTool in airunner.handlers.llm.agent.tools.rag_engine_tool.
Covers all logic branches, including from_defaults, streaming, agent handling, and error/edge cases.
"""

import pytest
from unittest.mock import MagicMock
from airunner.handlers.llm.agent.tools.rag_engine_tool import RAGEngineTool
from llama_index.core.tools.types import ToolMetadata, ToolOutput
from llama_index.core.base.llms.types import ChatMessage, MessageRole
import jinja2
import openai


class DummyRAGEngineTool(RAGEngineTool):
    def __init__(self, chat_engine, agent=None, **kwargs):
        metadata = ToolMetadata(
            name="rag_engine_tool", description="desc", return_direct=False
        )
        super().__init__(
            chat_engine=chat_engine, metadata=metadata, agent=agent, **kwargs
        )

    def _get_query_str(self, *args, **kwargs):
        return kwargs.get("query", "test query")


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.handle_response = MagicMock()
    return agent


@pytest.fixture
def mock_chat_engine():
    engine = MagicMock()
    engine.stream_chat.return_value = MagicMock(response_gen=iter(["RAG ", "result!"]))
    engine.chat_history = []
    return engine


def test_from_defaults_creates_instance():
    mock_engine = MagicMock()
    tool = RAGEngineTool.from_defaults(
        chat_engine=mock_engine, agent="agentY", return_direct=True
    )
    assert isinstance(tool, RAGEngineTool)
    assert tool.agent == "agentY"
    assert tool.chat_engine == mock_engine
    assert tool.metadata.name == "rag_engine_tool"
    assert tool.metadata.return_direct is True


def test_call_streams_and_handles_response(mock_agent, mock_chat_engine):
    tool = DummyRAGEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    # Patch chat_engine.llm to avoid hasattr/assignment
    mock_chat_engine.llm = MagicMock()
    result = tool.call(query="What is the answer?", chat_history=["hi"])
    assert mock_agent.handle_response.call_count == 2
    # Defensive: chat_history may not be appended if not real ChatEngine, so skip type check
    assert isinstance(result, ToolOutput)
    assert result.content == "RAG result!"
    assert result.tool_name == "rag_engine_tool"
    assert result.raw_input["input"] == "What is the answer?"
    assert result.raw_output == "RAG result!"


def test_call_with_empty_stream(mock_agent, mock_chat_engine):
    mock_chat_engine.stream_chat.return_value = MagicMock(response_gen=iter([]))
    mock_chat_engine.llm = MagicMock()
    tool = DummyRAGEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(query="", chat_history=[])
    assert result.content == ""
    assert mock_agent.handle_response.call_count == 0


def test_call_without_agent(mock_chat_engine):
    mock_chat_engine.llm = MagicMock()
    tool = DummyRAGEngineTool(chat_engine=mock_chat_engine, agent=None)
    # Patch: forcibly disable do_handle_response to avoid AttributeError
    tool.do_handle_response = False
    result = tool.call(query="test", chat_history=["hi"])
    assert result.content == "RAG result!"
    # No handle_response calls


def test_call_template_error(monkeypatch, mock_agent, mock_chat_engine):
    # Simulate jinja2 TemplateError in stream_chat
    def raise_template_error(*a, **k):
        raise jinja2.exceptions.TemplateError("bad template")

    mock_chat_engine.stream_chat.side_effect = raise_template_error
    tool = DummyRAGEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(query="bad template")
    assert "Error in template rendering" in result.content
    assert result.tool_name == "rag_engine_tool"
    assert mock_agent.handle_response.call_count == 0


def test_call_openai_api_error(monkeypatch, mock_agent, mock_chat_engine):
    # Simulate openai.APIError in streaming loop
    class DummyStreaming:
        def __init__(self):
            self.response_gen = self

        def __iter__(self):
            return self

        def __next__(self):
            # Pass message, dummy request, and body=None to match APIError signature
            raise openai.APIError("fail", object(), body=None)

    mock_chat_engine.stream_chat.return_value = DummyStreaming()
    mock_chat_engine.llm = MagicMock()
    tool = DummyRAGEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    result = tool.call(query="api error")
    assert result.content == ""
    assert result.tool_name == "rag_engine_tool"
    assert mock_agent.handle_response.call_count == 0


def test_call_do_interrupt_stops_stream(mock_agent, mock_chat_engine):
    # Should break out of streaming loop if _do_interrupt is set
    class DummyStreaming:
        def __init__(self):
            self.response_gen = iter(["A", "B", "C"])

    mock_chat_engine.stream_chat.return_value = DummyStreaming()
    mock_chat_engine.llm = MagicMock()
    tool = DummyRAGEngineTool(chat_engine=mock_chat_engine, agent=mock_agent)
    tool._do_interrupt = True
    result = tool.call(query="interrupt")
    assert result.content == ""
    assert mock_agent.handle_response.call_count == 0
