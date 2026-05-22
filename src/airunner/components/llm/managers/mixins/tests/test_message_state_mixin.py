"""Unit tests for the shared node-functions message-state helper."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from airunner.components.llm.managers.mixins.node_functions import (
    MessageStateMixin,
)


class _TestableMessageStateMixin(MessageStateMixin):
    """Minimal harness for message-state helper tests."""


def test_get_current_turn_messages_returns_latest_turn_only():
    """Current-turn slicing should start at the latest human message."""
    mixin = _TestableMessageStateMixin()
    messages = [
        HumanMessage(content="old question"),
        AIMessage(content="old answer", tool_calls=[]),
        HumanMessage(content="new question"),
        AIMessage(content="", tool_calls=[]),
    ]

    assert mixin._get_current_turn_messages(messages) == messages[2:]


def test_combine_tool_results_preserves_order_and_headers():
    """Combined tool output should preserve tool order and separators."""
    mixin = _TestableMessageStateMixin()
    tool_messages = [
        ToolMessage(content="First result", tool_call_id="tool-1", name="a"),
        ToolMessage(content="Second result", tool_call_id="tool-2", name="b"),
    ]

    combined = mixin._combine_tool_results(tool_messages)

    assert combined == (
        "\n--- Tool Result 1 ---\n"
        "First result\n"
        "\n--- Tool Result 2 ---\n"
        "Second result\n"
    )