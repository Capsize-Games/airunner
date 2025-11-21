"""
Unit tests for generation tools.

Tests direct text generation tools that produce output without
conversational wrappers.
"""

import pytest
from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)
from airunner.components.llm.tools.generation_tools import (
    generate_direct_response,
    generate_description,
    categorize,
)


class TestGenerationToolsRegistration:
    """Test that generation tools are properly registered."""

    def test_generation_category_exists(self):
        """Test that GENERATION category exists in ToolCategory enum."""
        assert hasattr(ToolCategory, "GENERATION")
        assert ToolCategory.GENERATION.value == "generation"

    def test_generate_direct_response_registered(self):
        """Test that generate_direct_response is registered."""
        tool = ToolRegistry.get("generate_direct_response")
        assert tool is not None
        assert tool.name == "generate_direct_response"
        assert tool.category == ToolCategory.GENERATION
        assert tool.return_direct is True
        assert tool.requires_agent is True

    def test_generate_description_registered(self):
        """Test that generate_description is registered."""
        tool = ToolRegistry.get("generate_description")
        assert tool is not None
        assert tool.name == "generate_description"
        assert tool.category == ToolCategory.GENERATION
        assert tool.return_direct is True
        assert tool.requires_agent is True

    def test_categorize_registered(self):
        """Test that categorize is registered."""
        tool = ToolRegistry.get("categorize")
        assert tool is not None
        assert tool.name == "categorize"
        assert tool.category == ToolCategory.ANALYSIS
        assert tool.return_direct is True
        assert tool.requires_agent is True

    def test_generation_tools_by_category(self):
        """Test that tools can be retrieved by GENERATION category."""
        tools = ToolRegistry.get_by_category(ToolCategory.GENERATION)
        assert len(tools) >= 2
        tool_names = [t.name for t in tools]
        assert "generate_direct_response" in tool_names
        assert "generate_description" in tool_names


class TestGenerationToolsFunctionality:
    """Test the functionality of generation tools."""

    def test_generate_direct_response_without_agent(self):
        """Test generate_direct_response returns error without agent."""
        result = generate_direct_response("test prompt", agent=None)
        assert result == "Error: Agent not available"

    def test_generate_direct_response_with_agent(self):
        """Test generate_direct_response with mock agent."""

        class MockAgent:
            pass

        agent = MockAgent()
        result = generate_direct_response("Write a description", agent=agent)

        # Should return a marker for direct generation
        assert result.startswith("__DIRECT_GENERATION_REQUEST__:")
        assert "Write a description" in result

    def test_generate_description_without_agent(self):
        """Test generate_description returns error without agent."""
        result = generate_description("Book Title", "Content here", agent=None)
        assert result == "Error: Agent not available"

    def test_generate_description_with_agent(self):
        """Test generate_description with mock agent."""

        class MockAgent:
            pass

        agent = MockAgent()
        result = generate_description(
            "Test Book", "Sample content", agent=agent
        )

        # Should return a marker with structured prompt
        assert result.startswith("__DIRECT_GENERATION_REQUEST__:")
        assert "Test Book" in result
        assert "Sample content" in result

    def test_categorize_without_agent(self):
        """Test categorize returns error without agent."""
        result = categorize("Book", "Content", agent=None)
        assert result == "Error: Agent not available"

    def test_categorize_with_agent(self):
        """Test categorize with mock agent."""

        class MockAgent:
            pass

        agent = MockAgent()
        result = categorize("Horror Novel", "Scary content", agent=agent)

        # Should return a marker with categorization prompt
        assert result.startswith("__DIRECT_GENERATION_REQUEST__:")
        assert "Horror Novel" in result
        assert "Scary content" in result


class TestGenerationToolsMetadata:
    """Test metadata and descriptions of generation tools."""

    def test_tool_descriptions_are_clear(self):
        """Test that tool descriptions clearly explain non-conversational output."""
        direct_tool = ToolRegistry.get("generate_direct_response")
        assert (
            "without conversational wrappers"
            in direct_tool.description.lower()
        )
        assert "direct" in direct_tool.description.lower()

        desc_tool = ToolRegistry.get("generate_description")
        assert (
            "without conversational preamble" in desc_tool.description.lower()
        )
        assert "description" in desc_tool.description.lower()

    def test_all_generation_tools_return_direct(self):
        """Test that all GENERATION tools have return_direct=True."""
        tools = ToolRegistry.get_by_category(ToolCategory.GENERATION)
        for tool in tools:
            assert (
                tool.return_direct is True
            ), f"{tool.name} should return directly"

    def test_all_generation_tools_require_agent(self):
        """Test that all GENERATION tools require an agent."""
        tools = ToolRegistry.get_by_category(ToolCategory.GENERATION)
        for tool in tools:
            assert (
                tool.requires_agent is True
            ), f"{tool.name} should require agent"
