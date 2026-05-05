"""Unit tests for ToolFilteringMixin."""

from unittest.mock import Mock

from airunner.components.llm.managers.mixins.tool_filtering_mixin import (
    ToolFilteringMixin,
)
from airunner.enums import LLMActionType


class _DummyToolFilteringMixin(ToolFilteringMixin):
    ALWAYS_INCLUDE_CATEGORIES = {"knowledge"}

    def __init__(self, supports_function_calling: bool):
        self.logger = Mock()
        self.supports_function_calling = supports_function_calling
        self._workflow_manager = Mock()
        self._tool_manager = Mock()


def test_code_requests_leave_tool_choice_unset_without_native_support():
    """Non-native models should not be forced into tool-only code turns."""
    mixin = _DummyToolFilteringMixin(supports_function_calling=False)
    tools = [Mock(name="create_code_file")]
    mixin._tool_manager.get_tools_by_categories.return_value = tools

    mixin._apply_tool_filter(["code"], action=LLMActionType.CODE)

    mixin._workflow_manager.update_tools.assert_called_once_with(
        tools,
        tool_choice=None,
    )


def test_code_requests_force_tool_choice_when_supported():
    """Native function-calling models may still force a code tool turn."""
    mixin = _DummyToolFilteringMixin(supports_function_calling=True)
    tools = [Mock(name="create_code_file")]
    mixin._tool_manager.get_tools_by_categories.return_value = tools

    mixin._apply_tool_filter(["code"], action=LLMActionType.CODE)

    mixin._workflow_manager.update_tools.assert_called_once_with(
        tools,
        tool_choice="any",
    )