"""Tests for GPT-OSS parsing helpers."""

from airunner.components.llm.utils.gpt_oss_parser import (
    looks_like_tool_argument_payload,
)


def test_tool_payload_detector_accepts_complete_tool_arguments():
    """Complete JSON tool arguments should be recognized."""
    content = (
        '{"file_path":"src/mazes/__main__.py",'
        '"content":"print(123)"}'
    )

    assert looks_like_tool_argument_payload(content) is True


def test_tool_payload_detector_accepts_truncated_tool_arguments():
    """Truncated JSON tool arguments should still be recognized."""
    content = (
        '{"file_path":"src/mazes/__main__.py",'
        '"content":"print'
    )

    assert looks_like_tool_argument_payload(content) is True


def test_tool_payload_detector_rejects_structured_final_response():
    """Structured summaries should not be mistaken for tool arguments."""
    content = (
        '{"result":{"file_path":"src/mazes/__main__.py"},'
        '"summary":"Created the file."}'
    )

    assert looks_like_tool_argument_payload(content) is False