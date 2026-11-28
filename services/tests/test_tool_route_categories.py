"""Unit tests for ToolFilteringMixin._route_categories.

_route_categories was extracted to keep _auto_select_tool_categories
within the long-function threshold. These tests pin the priority
order: direct route, greeting, no-tool, constrained, search trigger,
classifier fallback.
"""

from unittest.mock import MagicMock

from airunner_services.llm.managers.mixins.tool_filtering_mixin import (
    ToolFilteringMixin,
)


def _make_obj():
    obj = ToolFilteringMixin.__new__(ToolFilteringMixin)
    obj.logger = MagicMock()
    for name in (
        "_is_simple_greeting_prompt",
        "_is_simple_no_tool_prompt",
        "_is_constrained_reply_prompt",
        "_has_search_trigger_prompt",
        "_classify_prompt_for_tools",
    ):
        setattr(obj, name, MagicMock(return_value=False))
    obj._classify_prompt_for_tools.return_value = ["classified"]
    return obj


def test_direct_route_wins_immediately():
    obj = _make_obj()
    out = obj._route_categories("p", ["direct"], "tool", True)
    assert out == ["direct"]
    obj._is_simple_greeting_prompt.assert_not_called()


def test_greeting_disables_tools():
    obj = _make_obj()
    obj._is_simple_greeting_prompt.return_value = True
    out = obj._route_categories("hi", None, None, True)
    assert out == []
    obj._is_simple_no_tool_prompt.assert_not_called()


def test_no_tool_prompt_disables_tools():
    obj = _make_obj()
    obj._is_simple_no_tool_prompt.return_value = True
    out = obj._route_categories("p", None, None, True)
    assert out == []
    obj._is_constrained_reply_prompt.assert_not_called()


def test_constrained_reply_disables_tools():
    obj = _make_obj()
    obj._is_constrained_reply_prompt.return_value = True
    out = obj._route_categories("p", None, None, True)
    assert out == []
    obj._has_search_trigger_prompt.assert_not_called()


def test_search_trigger_forces_search():
    obj = _make_obj()
    obj._has_search_trigger_prompt.return_value = True
    out = obj._route_categories("search it", None, None, True)
    assert out == ["search"]
    obj._classify_prompt_for_tools.assert_not_called()


def test_classifier_fallback():
    obj = _make_obj()
    out = obj._route_categories("complex prompt", None, None, False)
    assert out == ["classified"]
    obj._classify_prompt_for_tools.assert_called_once_with(
        "complex prompt", allow_thinking=False
    )
