"""Tests for GPT-OSS parsing helpers."""

from airunner.components.llm.utils.gpt_oss_parser import (
    looks_like_tool_call_payload,
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


def test_tool_call_payload_detector_accepts_direct_tool_query_json():
    """Direct tool-call payloads should be recognized structurally."""
    content = '{"tool":"rag_search","query":"document title"}'

    assert looks_like_tool_call_payload(content) is True


def test_tool_call_payload_detector_accepts_truncated_name_args_json():
    """Truncated tool-call JSON should still be recognized."""
    content = '{"name":"read_file","args":{"path":"src/app.py"'

    assert looks_like_tool_call_payload(content) is True


def test_tool_call_payload_detector_rejects_plain_named_content_json():
    """Ordinary structured assistant JSON should not look like a tool call."""
    content = '{"name":"Alice","content":"Hello there"}'

    assert looks_like_tool_call_payload(content) is False