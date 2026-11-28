"""Prefilled GPT-OSS tool calls must produce a normalized tool call.

Regression coverage for the parser path that builds the final tool call
from a forced-tool-choice reply body.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from airunner_services.llm.adapters.chat_gguf_tool_parsing_gpt_oss import (
    parse_prefilled_gpt_oss_tool_call,
)


def _forced_adapter(choice: str = "lookup") -> SimpleNamespace:
    return SimpleNamespace(
        tool_choice=choice,
        tools=[{"function": {"name": "lookup"}}],
        logger=logging.getLogger(__name__),
        _use_raw_gpt_oss_completion=lambda: True,
    )


class TestPrefilledToolCall:
    def test_json_body_becomes_lookup_call(self) -> None:
        result = parse_prefilled_gpt_oss_tool_call(
            _forced_adapter(), '{"term": "quokka"}'
        )

        assert [call["name"] for call in result] == ["lookup"]
        assert result[0]["args"] == {"term": "quokka"}
        assert result[0]["type"] == "tool_call"
        assert result[0]["id"]

    def test_embedded_newlines_survive_parsing(self) -> None:
        result = parse_prefilled_gpt_oss_tool_call(
            _forced_adapter(), '{"script": "one\\ntwo"}'
        )

        assert result[0]["args"]["script"] == "one\ntwo"

    @pytest.mark.parametrize("choice", ["auto", None])
    def test_unforced_reply_yields_no_calls(self, choice) -> None:
        assert parse_prefilled_gpt_oss_tool_call(_forced_adapter(choice), "{}") == []
