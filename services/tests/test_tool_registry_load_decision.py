"""Unit tests for ToolRegistry default-load decisions.

_should_load_default_tools was extracted to keep
_ensure_default_tools_loaded within the long-function threshold.
These tests pin the name/category/fallback conditions.
"""

import pytest

from airunner_services.llm.core.tool_registry import ToolCategory, ToolRegistry


@pytest.fixture(autouse=True)
def _isolated_registry():
    ToolRegistry._tools.clear()
    ToolRegistry._categories.clear()
    yield
    ToolRegistry._tools.clear()
    ToolRegistry._categories.clear()


def test_missing_name_triggers_load():
    assert (
        ToolRegistry._should_load_default_tools(required_name="x") is True
    )


def test_present_name_skips_load():
    ToolRegistry._tools["x"] = object()
    assert (
        ToolRegistry._should_load_default_tools(required_name="x") is False
    )


def test_missing_category_triggers_load():
    assert (
        ToolRegistry._should_load_default_tools(
            required_category=ToolCategory.SEARCH
        )
        is True
    )


def test_present_category_skips_load():
    ToolRegistry._categories[ToolCategory.SEARCH] = ["t"]
    assert (
        ToolRegistry._should_load_default_tools(
            required_category=ToolCategory.SEARCH
        )
        is False
    )


def test_empty_registry_fallback_loads():
    assert (
        ToolRegistry._should_load_default_tools() is True
    )


def test_nonempty_registry_no_context_skips():
    ToolRegistry._tools["x"] = object()
    assert ToolRegistry._should_load_default_tools() is False
