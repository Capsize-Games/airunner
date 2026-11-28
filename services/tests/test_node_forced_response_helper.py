"""Unit tests for NodeForcedResponseHelper.force_response_node.

The branch helpers were extracted to keep force_response_node within the
long-function threshold. These tests pin the dispatch: no tool message,
workflow-tool continuation, direct tool return, and generated forced
response.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from airunner_services.llm.managers.mixins.node_forced_response_helper import (
    NodeForcedResponseHelper,
)


def _make_helper(owner):
    helper = NodeForcedResponseHelper.__new__(NodeForcedResponseHelper)
    helper._owner = owner
    helper.should_return_tool_direct = MagicMock(return_value=False)
    helper.create_workflow_continuation_message = MagicMock(return_value="cont")
    helper.create_direct_tool_response_message = MagicMock(return_value="direct")
    helper.generate_forced_response_message = MagicMock(return_value="forced")
    return helper


def _ai_with_tool(name="search"):
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": {}, "id": "1"}]
    )


def _tool_message(content="result"):
    return ToolMessage(content=content, tool_call_id="x")


def _human(content="why?"):
    return HumanMessage(content=content)


def _state(messages):
    return {"messages": messages, "generation_kwargs": {}}


def test_no_tool_message_returns_empty():
    owner = MagicMock()
    owner.WORKFLOW_TOOLS = []
    helper = _make_helper(owner)
    result = helper.force_response_node(_state([_human(), _tool_message()]))
    assert result == {"messages": []}
    owner.logger.error.assert_called()


def test_workflow_tool_routes_to_continuation():
    owner = MagicMock()
    owner.WORKFLOW_TOOLS = ["search"]
    helper = _make_helper(owner)
    state = _state([_human(), _ai_with_tool("search"), _tool_message("r1")])
    result = helper.force_response_node(state)
    assert result == {"messages": ["cont"], "workflow_continuation": True}
    helper.create_workflow_continuation_message.assert_called_once()


def test_direct_tool_returns_direct_message():
    owner = MagicMock()
    owner.WORKFLOW_TOOLS = []
    helper = _make_helper(owner)
    helper.should_return_tool_direct.return_value = True
    state = _state([_human(), _ai_with_tool("search"), _tool_message("r1")])
    result = helper.force_response_node(state)
    assert result == {"messages": ["direct"], "workflow_continuation": False}
    helper.create_direct_tool_response_message.assert_called_once()


def test_generated_forced_path():
    owner = MagicMock()
    owner.WORKFLOW_TOOLS = []
    helper = _make_helper(owner)
    helper.generate_forced_response_message.return_value = SimpleNamespace(
        content="answer"
    )
    state = _state([_human("q?"), _ai_with_tool("search"), _tool_message("r1")])
    result = helper.force_response_node(state)
    assert result["workflow_continuation"] is False
    assert result["messages"][0].content == "answer"
    helper.generate_forced_response_message.assert_called_once()


def test_last_tool_message_wins():
    owner = MagicMock()
    owner.WORKFLOW_TOOLS = []
    helper = _make_helper(owner)
    helper.generate_forced_response_message.return_value = SimpleNamespace(
        content="answer"
    )
    state = _state(
        [
            _human(),
            _ai_with_tool("first"),
            _tool_message("r1"),
            _ai_with_tool("second"),
            _tool_message("r2"),
        ]
    )
    helper.force_response_node(state)
    args, _ = helper.generate_forced_response_message.call_args
    assert args[1] == "second"
