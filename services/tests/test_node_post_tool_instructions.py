"""Unit tests for NodePostToolInstructionsHelper._build_instruction.

The metrics gathering was extracted to keep the instruction builder
within the long-function threshold. These tests pin the metric counts,
the research-mode dispatch, and the response-format branches.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from airunner_services.llm.managers.mixins.node_post_tool_instructions_helper import (
    NodePostToolInstructionsHelper,
)


def _make_helper(owner):
    helper = NodePostToolInstructionsHelper.__new__(
        NodePostToolInstructionsHelper
    )
    helper._owner = owner
    helper._research_helper = MagicMock()
    helper._research_helper.scrape_counts.return_value = (1, 0)
    helper._research_helper.search_urls.return_value = ["http://x"]
    helper._research_helper.research_instruction.return_value = "research"
    helper._default_instruction = MagicMock(return_value="default")
    return helper


def _owner(response_format=None, force_tool=None):
    owner = MagicMock()
    owner._response_format = response_format
    owner._force_tool = force_tool
    owner._chat_model.tool_calling_mode = "react"
    return owner


def _ai(tool_name):
    return AIMessage(content="", tool_calls=[{"name": tool_name, "args": {}, "id": "1"}])


def test_research_mode_dispatches_to_research_instruction():
    owner = _owner(force_tool="search_web")
    helper = _make_helper(owner)
    out = helper._build_instruction(
        [HumanMessage(content="q"), _ai("search_web")],
        [ToolMessage(content="r", tool_call_id="x")],
    )
    assert out == "research"
    helper._research_helper.research_instruction.assert_called_once()


def test_json_format_requires_json_only():
    owner = _owner(response_format="json")
    helper = _make_helper(owner)
    out = helper._build_instruction([], [])
    assert "ONLY with valid JSON" in out


def test_named_format_uses_format_name():
    owner = _owner(response_format="xml")
    helper = _make_helper(owner)
    out = helper._build_instruction([], [])
    assert "Respond in xml format." in out


def test_conversational_falls_back_to_default():
    owner = _owner(response_format="conversational")
    helper = _make_helper(owner)
    out = helper._build_instruction([], [])
    assert out == "default"


def test_no_format_falls_back_to_default():
    owner = _owner(response_format=None)
    helper = _make_helper(owner)
    out = helper._build_instruction([], [])
    assert out == "default"


def test_metrics_count_scrape_attempts():
    owner = _owner()
    helper = _make_helper(owner)
    _, _, metrics = helper._gather_tool_flow_metrics(
        [_ai("scrape_website"), _ai("search_web"), _ai("scrape_website")],
        [],
    )
    assert metrics["scrape_attempts"] == 2
    assert metrics["tool_call_count"] == 3
    assert metrics["successful_scrapes"] == 1
    assert metrics["search_urls"] == ["http://x"]
