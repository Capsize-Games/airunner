"""
Unit tests for tool schema utilities.

Tests parameter extraction, schema generation, and example formatting.
"""

import pytest
from typing import Annotated, Optional, List, Dict

from airunner.components.llm.core.tool_schema import (
    python_type_to_json_type,
    get_annotated_description,
    get_base_type,
    get_function_schema,
    get_tool_schema_with_examples,
    format_tool_for_llm,
)
from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolInfo,
    ToolCategory,
    tool,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before and after each test."""
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


class TestPythonTypeToJsonType:
    """Tests for python_type_to_json_type."""

    def test_string_type(self):
        assert python_type_to_json_type(str) == "string"

    def test_int_type(self):
        assert python_type_to_json_type(int) == "integer"

    def test_float_type(self):
        assert python_type_to_json_type(float) == "number"

    def test_bool_type(self):
        assert python_type_to_json_type(bool) == "boolean"

    def test_list_type(self):
        assert python_type_to_json_type(list) == "array"

    def test_dict_type(self):
        assert python_type_to_json_type(dict) == "object"

    def test_optional_type(self):
        """Optional[str] should resolve to string."""
        assert python_type_to_json_type(Optional[str]) == "string"

    def test_list_generic(self):
        """List[str] should resolve to array."""
        assert python_type_to_json_type(List[str]) == "array"

    def test_dict_generic(self):
        """Dict[str, int] should resolve to object."""
        assert python_type_to_json_type(Dict[str, int]) == "object"


class TestGetAnnotatedDescription:
    """Tests for get_annotated_description."""

    def test_annotated_with_description(self):
        """Should extract description from Annotated type."""
        annotated = Annotated[str, "A search query"]
        result = get_annotated_description(annotated)
        assert result == "A search query"

    def test_plain_type(self):
        """Plain types should return None."""
        result = get_annotated_description(str)
        assert result is None

    def test_annotated_without_string(self):
        """Annotated without string metadata should return None."""
        annotated = Annotated[str, 123]
        result = get_annotated_description(annotated)
        assert result is None


class TestGetBaseType:
    """Tests for get_base_type."""

    def test_plain_type(self):
        assert get_base_type(str) == str

    def test_optional_type(self):
        """Optional[str] should return str."""
        assert get_base_type(Optional[str]) == str

    def test_annotated_type(self):
        """Annotated[str, 'desc'] should return str."""
        annotated = Annotated[str, "description"]
        assert get_base_type(annotated) == str

    def test_nested_annotated_optional(self):
        """Should handle Annotated[Optional[str], 'desc']."""
        annotated = Annotated[Optional[str], "description"]
        # Should get to str
        assert get_base_type(annotated) == str


class TestGetFunctionSchema:
    """Tests for get_function_schema."""

    def test_simple_function(self):
        """Should extract schema from simple function."""
        def my_func(name: str, count: int) -> str:
            return name * count

        schema = get_function_schema(my_func)
        
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert "count" in schema["properties"]
        assert schema["properties"]["count"]["type"] == "integer"
        assert "name" in schema["required"]
        assert "count" in schema["required"]

    def test_function_with_defaults(self):
        """Optional parameters should not be required."""
        def my_func(query: str, limit: int = 10) -> str:
            return query

        schema = get_function_schema(my_func)
        
        assert "query" in schema["required"]
        assert "limit" not in schema["required"]

    def test_function_with_annotated(self):
        """Should extract descriptions from Annotated types."""
        def my_func(
            query: Annotated[str, "The search query"],
        ) -> str:
            return query

        schema = get_function_schema(my_func)
        
        assert schema["properties"]["query"]["description"] == "The search query"

    def test_excludes_special_params(self):
        """Should exclude self, cls, api, agent parameters."""
        def my_func(self, query: str, api=None, agent=None) -> str:
            return query

        schema = get_function_schema(my_func)
        
        assert "self" not in schema["properties"]
        assert "api" not in schema["properties"]
        assert "agent" not in schema["properties"]
        assert "query" in schema["properties"]


class TestGetToolSchemaWithExamples:
    """Tests for get_tool_schema_with_examples."""

    def test_generates_full_schema(self):
        """Should generate complete schema with examples."""
        @tool(
            name="test_tool",
            category=ToolCategory.SYSTEM,
            description="A test tool",
            input_examples=[
                {"query": "example 1"},
                {"query": "example 2"},
            ],
        )
        def test_func(query: str) -> str:
            return query

        tool_info = ToolRegistry.get("test_tool")
        schema = get_tool_schema_with_examples(tool_info)
        
        assert schema["name"] == "test_tool"
        assert schema["description"] == "A test tool"
        assert "input_schema" in schema
        assert "properties" in schema["input_schema"]
        assert len(schema["input_examples"]) == 2

    def test_schema_without_examples(self):
        """Schema without examples should not have input_examples key."""
        @tool(
            name="no_examples_tool",
            category=ToolCategory.SYSTEM,
            description="No examples",
        )
        def no_examples_func() -> str:
            return "result"

        tool_info = ToolRegistry.get("no_examples_tool")
        schema = get_tool_schema_with_examples(tool_info)
        
        assert "input_examples" not in schema or schema.get("input_examples") == []


class TestFormatToolForLLM:
    """Tests for format_tool_for_llm."""

    def test_formats_tool_info(self):
        """Should format tool info as readable string."""
        @tool(
            name="format_test_tool",
            category=ToolCategory.SEARCH,
            description="A tool for testing formatting",
            input_examples=[{"query": "test"}],
        )
        def format_test(
            query: Annotated[str, "The search query"],
            limit: Annotated[int, "Max results"] = 10,
        ) -> str:
            return query

        tool_info = ToolRegistry.get("format_test_tool")
        formatted = format_tool_for_llm(tool_info)
        
        assert "format_test_tool" in formatted
        assert "search" in formatted.lower()
        assert "A tool for testing formatting" in formatted
        assert "query" in formatted
        assert "(required)" in formatted
        assert "limit" in formatted
        assert "(optional)" in formatted

    def test_includes_examples_by_default(self):
        """Examples should be included by default."""
        @tool(
            name="example_format_tool",
            category=ToolCategory.SYSTEM,
            description="Test",
            input_examples=[{"x": 1}],
        )
        def example_func(x: int) -> int:
            return x

        tool_info = ToolRegistry.get("example_format_tool")
        formatted = format_tool_for_llm(tool_info, include_examples=True)
        
        assert "Examples:" in formatted
        assert '"x": 1' in formatted

    def test_excludes_examples_when_requested(self):
        """Examples can be excluded."""
        @tool(
            name="no_example_format_tool",
            category=ToolCategory.SYSTEM,
            description="Test",
            input_examples=[{"x": 1}],
        )
        def no_example_func(x: int) -> int:
            return x

        tool_info = ToolRegistry.get("no_example_format_tool")
        formatted = format_tool_for_llm(tool_info, include_examples=False)
        
        assert "Examples:" not in formatted
