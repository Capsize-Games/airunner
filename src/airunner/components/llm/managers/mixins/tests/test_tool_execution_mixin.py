"""Unit tests for ToolExecutionMixin tool-arg normalization."""

from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

from airunner.components.llm.managers.mixins.tool_execution_mixin import (
    ToolExecutionMixin,
)


class _DummyToolExecutionMixin(ToolExecutionMixin):
    def __init__(self):
        self.logger = Mock()
        self._conversation_id = None
        self._executed_tools = []


def test_normalize_rag_search_uses_latest_user_prompt_when_query_missing():
    """Malformed rag_search args should be repaired to the user question."""
    mixin = _DummyToolExecutionMixin()
    messages = [
        HumanMessage(content="what is this document?"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "tool-1",
                    "name": "rag_search",
                    "args": {
                        "fact": "User asked about a document",
                        "section": "overview",
                    },
                }
            ],
        ),
    ]

    updated_messages, tool_calls = mixin._normalize_tool_calls_for_execution(
        messages,
        messages[-1].tool_calls,
    )

    assert len(tool_calls) == 1
    assert tool_calls[0]["id"] == "tool-1"
    assert tool_calls[0]["name"] == "rag_search"
    assert tool_calls[0]["args"] == {"query": "what is this document?"}
    assert updated_messages[-1].tool_calls[0]["args"] == {
        "query": "what is this document?"
    }