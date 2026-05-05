"""Tests for visible chat request modes."""

from airunner.components.chat.gui.widgets.chat_request_mode import (
    chat_request_modes,
    get_chat_request_mode,
)
from airunner.enums import LLMActionType


def test_get_chat_request_mode_defaults_to_ask():
    """Unknown request-mode keys should fall back to Ask."""

    mode = get_chat_request_mode("missing")

    assert mode.key == "ask"
    assert mode.action is LLMActionType.CHAT


def test_visible_chat_request_modes_include_plan_and_agent():
    """The footer should expose Ask, Plan, and Agent modes."""

    modes = {mode.key: mode for mode in chat_request_modes()}

    assert list(modes) == ["ask", "plan", "agent"]
    assert modes["plan"].use_mode_routing is True
    assert modes["plan"].mode_override == "code"
    assert "Do not edit files" in modes["plan"].prompt_prefix
    assert modes["agent"].action is LLMActionType.CODE
    assert modes["agent"].use_mode_routing is True
