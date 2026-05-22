"""Unit tests for ToolFilteringMixin."""

from types import SimpleNamespace
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


def test_code_requests_do_not_force_tool_choice_when_supported():
    """Legacy code actions no longer force a code-only tool turn."""
    mixin = _DummyToolFilteringMixin(supports_function_calling=True)
    tools = [Mock(name="create_code_file")]
    mixin._tool_manager.get_tools_by_categories.return_value = tools

    mixin._apply_tool_filter(["code"], action=LLMActionType.CODE)

    mixin._workflow_manager.update_tools.assert_called_once_with(
        tools,
        tool_choice=None,
    )


def test_allowed_tool_names_restrict_planner_visible_tools():
    """Allowlists should trim category results to the intended tools."""
    mixin = _DummyToolFilteringMixin(supports_function_calling=False)
    inspect_tool = SimpleNamespace(name="inspect_loaded_documents")
    analyze_tool = SimpleNamespace(name="analyze_loaded_document")
    rag_tool = SimpleNamespace(name="rag_search")
    search_tool = SimpleNamespace(name="search_web")
    knowledge_tool = SimpleNamespace(name="record_knowledge")
    mixin._tool_manager.get_tools_by_categories.return_value = [
        inspect_tool,
        analyze_tool,
        rag_tool,
        search_tool,
        knowledge_tool,
    ]

    mixin._apply_tool_filter(
        ["rag", "search"],
        action=LLMActionType.CHAT,
        allowed_tool_names=[
            "inspect_loaded_documents",
            "analyze_loaded_document",
            "rag_search",
        ],
    )

    mixin._workflow_manager.update_tools.assert_called_once_with(
        [inspect_tool, analyze_tool, rag_tool],
        tool_choice=None,
    )


def test_planner_mode_forces_tool_choice_for_document_allowlist():
    """Planner-controlled document turns should require one tool call."""
    mixin = _DummyToolFilteringMixin(supports_function_calling=True)
    mixin.llm_request = SimpleNamespace(planner_mode="select_tools")
    inspect_tool = SimpleNamespace(name="inspect_loaded_documents")
    analyze_tool = SimpleNamespace(name="analyze_loaded_document")
    rag_tool = SimpleNamespace(name="rag_search")
    mixin._tool_manager.get_tools_by_categories.return_value = [
        inspect_tool,
        analyze_tool,
        rag_tool,
    ]

    mixin._apply_tool_filter(
        ["rag"],
        action=LLMActionType.CHAT,
        allowed_tool_names=[
            "inspect_loaded_documents",
            "analyze_loaded_document",
            "rag_search",
        ],
    )

    mixin._workflow_manager.update_tools.assert_called_once_with(
        [inspect_tool, analyze_tool, rag_tool],
        tool_choice="any",
    )