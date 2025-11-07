"""Test code generation tool registration."""

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)


def test_code_generation_tools_registered():
    """Verify all code generation tools are registered."""
    expected_tools = [
        "create_code_file",
        "edit_code_file",
        "read_code_file",
        "validate_code",
        "format_code_file",
        "run_tests",
        "list_workspace_files",
        "delete_code_file",
    ]

    registered_tools = list(ToolRegistry._tools.keys())

    for tool_name in expected_tools:
        assert (
            tool_name in registered_tools
        ), f"Tool {tool_name} not registered"


def test_code_generation_tools_have_correct_category():
    """Verify code generation tools are in CODE category."""
    code_tools = [
        "create_code_file",
        "edit_code_file",
        "read_code_file",
        "validate_code",
        "format_code_file",
        "run_tests",
        "list_workspace_files",
        "delete_code_file",
    ]

    for tool_name in code_tools:
        if tool_name in ToolRegistry._tools:
            tool_info = ToolRegistry._tools[tool_name]
            assert (
                tool_info.category == ToolCategory.CODE
            ), f"Tool {tool_name} has wrong category: {tool_info.category}"


def test_code_tools_can_be_retrieved():
    """Verify code tools can be retrieved from registry."""
    # Access directly from registry
    assert "create_code_file" in ToolRegistry._tools
    tool_info = ToolRegistry._tools["create_code_file"]
    assert tool_info.name == "create_code_file"
    assert callable(tool_info.func)
    assert "Create a new code file" in tool_info.description


def test_code_tools_by_category():
    """Verify code tools can be retrieved by category."""
    code_tools = ToolRegistry.get_by_category(ToolCategory.CODE)

    # Should have at least our 8 new tools plus existing code tools
    tool_names = [tool.name for tool in code_tools]

    assert "create_code_file" in tool_names
    assert "validate_code" in tool_names
    assert "run_tests" in tool_names
