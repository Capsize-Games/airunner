"""Unit tests for ToolExecutionMixin tool-arg normalization."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, HumanMessage

from airunner.components.llm.managers.mixins.tool_execution_mixin import (
    ToolExecutionMixin,
)


class _DummyToolExecutionMixin(ToolExecutionMixin):
    def __init__(self):
        self.logger = Mock()
        self._conversation_id = None
        self._executed_tools = []
        self._tool_choice = None
        self._force_tool = None
        self._tools = []
        self._rebound = False

    def _emit_starting_status(self, _tool_calls):
        return None

    def _sanitize_tool_functions(self):
        return None

    def _emit_completed_status(self, _result_state, _tool_calls):
        return None

    def _get_next_workflow_tool(self, _executed_tool):
        return None

    def _bind_tools_to_model(self):
        self._rebound = True


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


def test_execute_tools_with_status_clears_stale_tool_choice():
    """Clearing a forced tool should also clear the bound tool choice."""
    mixin = _DummyToolExecutionMixin()
    mixin._tools = [Mock(name="example_tool")]
    mixin._force_tool = "example_tool"
    mixin._tool_choice = {
        "type": "function",
        "function": {"name": "example_tool"},
    }

    state = {
        "messages": [
            HumanMessage(content="run the example tool"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "example_tool",
                        "args": {"text": "hello"},
                    }
                ],
            ),
        ]
    }

    fake_tool_node = Mock()
    fake_tool_node.invoke.return_value = {"messages": ["ok"]}

    with patch(
        "langgraph.prebuilt.ToolNode",
        return_value=fake_tool_node,
    ):
        result = mixin._execute_tools_with_status(state)

    assert result["messages"]
    assert mixin._force_tool is None
    assert mixin._tool_choice is None
    assert mixin._rebound is True


def test_normalize_rag_search_rewrites_low_info_document_followup():
    """A bare affirmative should not become a literal document search query."""
    mixin = _DummyToolExecutionMixin()
    mixin.llm_request = SimpleNamespace(document_answer_mode="synthesized")
    messages = [
        HumanMessage(content="what is this book about?"),
        AIMessage(
            content=(
                "Would you like me to search for more specific details "
                "about the plot or characters?"
            )
        ),
        HumanMessage(content="yes"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "tool-2",
                    "name": "rag_search",
                    "args": {"query": "yes"},
                }
            ],
        ),
    ]

    updated_messages, tool_calls = mixin._normalize_tool_calls_for_execution(
        messages,
        messages[-1].tool_calls,
    )

    assert tool_calls[0]["args"] == {
        "query": (
            "specific plot details, character information, and themes "
            "from this book"
        )
    }
    assert updated_messages[-1].tool_calls[0]["args"] == tool_calls[0]["args"]