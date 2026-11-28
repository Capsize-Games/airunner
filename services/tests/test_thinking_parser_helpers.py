"""Unit tests for the thinking-parser extraction helpers.

_closed_pattern_match and _incomplete_close_pattern were extracted
to keep parse_thinking_response within the long-function threshold.
These tests pin the closed-block extraction, the unclosed trailing
thinking, and the tag-format gating.
"""

from airunner_services.llm.thinking_parser import (
    ANGLE_THINK_PATTERN,
    BRACKET_THINK_PATTERN,
    _closed_pattern_match,
    _incomplete_close_pattern,
    parse_thinking_response,
)


def test_closed_match_extracts_thinking_and_content():
    response = "<think>planning</think>answer"
    out = _closed_pattern_match(
        response, [(ANGLE_THINK_PATTERN, "angle")]
    )
    assert out is not None
    assert out.thinking_content == "planning"
    assert out.content == "answer"
    assert out.tag_format == "angle"


def test_closed_match_returns_none_without_match():
    assert (
        _closed_pattern_match("plain", [(ANGLE_THINK_PATTERN, "angle")])
        is None
    )


def test_incomplete_angle_trailing_thinking():
    out = _incomplete_close_pattern("<think>still going", "auto")
    assert out is not None
    assert out.thinking_content == "still going"
    assert out.content == ""
    assert out.tag_format == "angle"


def test_incomplete_brackets_case_insensitive():
    out = _incomplete_close_pattern("pre [think]stuff", "auto")
    assert out is not None
    assert out.thinking_content == "stuff"
    assert out.tag_format == "brackets"


def test_incomplete_gated_by_tag_format():
    assert _incomplete_close_pattern("<think>x", "brackets") is None
    assert _incomplete_close_pattern("[THINK]x", "angle") is None


def test_incomplete_none_when_open_and_closed():
    assert _incomplete_close_pattern("<think>x</think>", "auto") is None


def test_parse_dispatch_closed_brackets():
    out = parse_thinking_response("[THINK]plan[/THINK]done", "brackets")
    assert out.thinking_content == "plan"
    assert out.content == "done"
    assert out.tag_format == "brackets"


def test_parse_no_thinking_returns_stripped_content():
    out = parse_thinking_response("  plain answer  ")
    assert out.thinking_content is None
    assert out.content == "plain answer"


def test_parse_empty_response():
    out = parse_thinking_response("")
    assert out.thinking_content is None
    assert out.content == ""
