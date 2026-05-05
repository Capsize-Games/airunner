"""Unit tests for parent graph response compilation."""

from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from airunner.components.llm.managers.parent_graph_builder import (
    ParentGraphBuilder,
)


def test_compile_response_keeps_only_terminal_ai_message():
    """Test routed subgraphs expose only the final assistant turn."""
    builder = ParentGraphBuilder(chat_model=Mock())
    tool_request = AIMessage(
        content="",
        tool_calls=[
            {"id": "tool-1", "name": "create_code_file", "args": {}}
        ],
    )
    tool_result = ToolMessage(
        content="created maze_generator.py",
        tool_call_id="tool-1",
        name="create_code_file",
    )
    final_message = AIMessage(content="Created the maze generator.")

    result = builder._compile_response(
        {
            "subgraph_result": {
                "messages": [
                    HumanMessage(content="write the file"),
                    tool_request,
                    tool_result,
                    final_message,
                ]
            }
        }
    )

    assert result["messages"] == [final_message]


def test_compile_response_prefers_last_visible_ai_message():
    """Test analysis-only tail messages do not hide prior visible output."""
    builder = ParentGraphBuilder(chat_model=Mock())
    visible_message = AIMessage(content="Created the maze generator.")
    hidden_message = AIMessage(
        content=(
            "<|channel|>analysis<|message|>Need to summarize."
            "<|return|>"
        )
    )

    result = builder._compile_response(
        {
            "subgraph_result": {
                "messages": [
                    HumanMessage(content="write the file"),
                    visible_message,
                    hidden_message,
                ]
            }
        }
    )

    assert result["messages"] == [visible_message]


def test_compile_response_skips_raw_tool_argument_payload():
    """Malformed tool payloads should not surface as final assistant text."""
    builder = ParentGraphBuilder(chat_model=Mock())
    raw_payload = AIMessage(
        content=(
            '{"file_path":"src/mazes/__main__.py",'
            '"content":"print'
        )
    )

    result = builder._compile_response(
        {
            "subgraph_result": {
                "messages": [
                    HumanMessage(content="write the file"),
                    raw_payload,
                ]
            }
        }
    )

    assert result["messages"] == []