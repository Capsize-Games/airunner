"""Unit tests for NodeFunctionsMixin RAG/search routing."""

from unittest.mock import Mock

from langchain_core.messages import AIMessage, ToolMessage

from airunner.components.llm.managers.mixins.node_functions_mixin import (
    NodeFunctionsMixin,
)


class _DummyNodeFunctions(NodeFunctionsMixin):
    def __init__(self):
        self.logger = Mock()

    def _should_return_tool_direct(self, tool_name: str) -> bool:
        return False


def test_route_after_tools_forces_response_for_rag_search():
    """RAG search results should synthesize a final answer directly."""
    mixin = _DummyNodeFunctions()
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "rag_search",
                        "args": {"query": "document summary"},
                    }
                ],
            ),
            ToolMessage(
                content="Found 1 relevant chunk.",
                tool_call_id="tool-1",
                name="rag_search",
            ),
        ]
    }

    assert mixin._route_after_tools(state) == "force_response"


def test_route_after_tools_keeps_search_web_in_model_loop():
    """Deep-research web search should still allow further tool use."""
    mixin = _DummyNodeFunctions()
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "search_web",
                        "args": {"query": "latest updates"},
                    }
                ],
            ),
            ToolMessage(
                content="Search results here.",
                tool_call_id="tool-1",
                name="search_web",
            ),
        ]
    }

    assert mixin._route_after_tools(state) == "model"