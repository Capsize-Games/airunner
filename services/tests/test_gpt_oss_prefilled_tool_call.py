"""parse_prefilled_gpt_oss_tool_call must build a tool call, not raise NameError.

The module used ``_tool_call`` without importing it, so a forced-tool-choice
Harmony reply that parsed successfully crashed on the final return.
"""

import logging
from types import SimpleNamespace

from airunner_services.llm.adapters.chat_gguf_tool_parsing_gpt_oss import (
    parse_prefilled_gpt_oss_tool_call,
)


def _adapter(tool_choice="search"):
    return SimpleNamespace(
        tool_choice=tool_choice,
        tools=[{"function": {"name": "search"}}],
        logger=logging.getLogger("test"),
        _use_raw_gpt_oss_completion=lambda: True,
    )


def test_prefilled_tool_call_is_built_from_json_body():
    calls = parse_prefilled_gpt_oss_tool_call(_adapter(), '{"query": "cats"}')

    assert len(calls) == 1
    assert calls[0]["name"] == "search"
    assert calls[0]["args"] == {"query": "cats"}
    assert calls[0]["type"] == "tool_call"
    assert calls[0]["id"]


def test_prefilled_tool_call_keeps_raw_newlines_in_arguments():
    calls = parse_prefilled_gpt_oss_tool_call(_adapter(), '{"code": "a\nb"}')

    assert calls[0]["args"] == {"code": "a\nb"}


def test_no_tool_call_without_forced_tool():
    assert parse_prefilled_gpt_oss_tool_call(_adapter(tool_choice="auto"), '{"q": 1}') == []
