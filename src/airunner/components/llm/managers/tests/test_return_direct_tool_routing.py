from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from airunner.components.llm.managers.mixins.node_functions_mixin import (
    NodeFunctionsMixin,
)


class DummyNodeFunctionsMixin(NodeFunctionsMixin):
    def __init__(self):
        self.logger = Mock()
        self._tools = []
        self._token_callback = None


def _make_tool(name: str, return_direct: bool):
    tool = Mock()
    tool.name = name
    tool.return_direct = return_direct
    return tool


class TestReturnDirectToolRouting:
    def test_route_after_tools_uses_force_response_for_return_direct_tool(self):
        mixin = DummyNodeFunctionsMixin()
        mixin._tools = [_make_tool("get_current_datetime", True)]
        state = {
            "messages": [
                HumanMessage(content="what time is it?"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "tool-call-1",
                            "name": "get_current_datetime",
                            "args": {},
                        }
                    ],
                ),
                ToolMessage(
                    content="Current local date and time: 2026-03-21 22:14:54.",
                    tool_call_id="tool-call-1",
                    name="get_current_datetime",
                ),
            ]
        }

        route = mixin._route_after_tools(state)

        assert route == "force_response"

    def test_force_response_node_returns_tool_content_directly(self):
        mixin = DummyNodeFunctionsMixin()
        mixin._tools = [_make_tool("get_current_datetime", True)]
        state = {
            "messages": [
                HumanMessage(content="what time is it?"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "tool-call-1",
                            "name": "get_current_datetime",
                            "args": {},
                        }
                    ],
                ),
                ToolMessage(
                    content="Current local date and time: 2026-03-21 22:14:54.",
                    tool_call_id="tool-call-1",
                    name="get_current_datetime",
                ),
            ]
        }

        result = mixin._force_response_node(state)

        assert result["workflow_continuation"] is False
        message = result["messages"][0]
        assert isinstance(message, AIMessage)
        assert message.content == "Current local date and time: 2026-03-21 22:14:54."
        assert message.tool_calls == []