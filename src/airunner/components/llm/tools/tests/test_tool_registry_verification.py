"""
Verification tests for tool registration and availability.

Ensures that all tools (calendar, web, search, etc.) are properly
registered in the ToolRegistry and available to the LLM agent.
"""

import pytest
from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)


class TestToolRegistryVerification:
    """Verify all expected tools are registered."""

    def test_web_tools_registered(self):
        """Verify web search and scraping tools are registered."""
        # Get all registered tools
        all_tools = ToolRegistry._tools

        # Check for search_web
        assert "search_web" in all_tools, "search_web tool not registered"
        search_tool = all_tools["search_web"]
        assert search_tool.category == ToolCategory.SEARCH
        assert "search" in search_tool.description.lower()

        # Check for scrape_website
        assert (
            "scrape_website" in all_tools
        ), "scrape_website tool not registered"
        scrape_tool = all_tools["scrape_website"]
        assert scrape_tool.category == ToolCategory.SEARCH
        assert "scrape" in scrape_tool.description.lower()

    def test_calendar_tools_registered(self):
        """Verify calendar management tools are registered."""
        all_tools = ToolRegistry._tools

        # Check for calendar event tools
        expected_calendar_tools = [
            "create_calendar_event",
            "list_calendar_events",
            "update_calendar_event",
            "delete_calendar_event",
        ]

        for tool_name in expected_calendar_tools:
            assert tool_name in all_tools, f"{tool_name} not registered"
            tool = all_tools[tool_name]
            assert tool.category == ToolCategory.SYSTEM

    def test_math_tools_registered(self):
        """Verify math computation tools are registered."""
        all_tools = ToolRegistry._tools

        expected_math_tools = [
            "sympy_compute",
            "numpy_compute",
            "python_compute",
        ]

        for tool_name in expected_math_tools:
            assert tool_name in all_tools, f"{tool_name} not registered"
            tool = all_tools[tool_name]
            assert tool.category == ToolCategory.MATH

    def test_image_tools_registered(self):
        """Verify image generation tools are registered."""
        all_tools = ToolRegistry._tools

        expected_image_tools = [
            "generate_image",
            "set_image_dimensions",
            "clear_canvas",
            "open_image",
        ]

        for tool_name in expected_image_tools:
            assert tool_name in all_tools, f"{tool_name} not registered"
            tool = all_tools[tool_name]
            assert tool.category == ToolCategory.IMAGE

    def test_system_tools_registered(self):
        """Verify system control tools are registered."""
        all_tools = ToolRegistry._tools

        expected_system_tools = [
            "quit_application",
            "toggle_tts",
            "list_directory",
            "read_file",
            "write_file",
        ]

        for tool_name in expected_system_tools:
            assert tool_name in all_tools, f"{tool_name} not registered"
            tool = all_tools[tool_name]
            assert tool.category in [ToolCategory.SYSTEM, ToolCategory.FILE]

    def test_conversation_tools_registered(self):
        """Verify conversation management tools are registered."""
        all_tools = ToolRegistry._tools

        expected_conv_tools = [
            "clear_chat_history",
            "get_conversation_summary",
            "load_conversation",
        ]

        for tool_name in expected_conv_tools:
            assert tool_name in all_tools, f"{tool_name} not registered"
            tool = all_tools[tool_name]
            assert tool.category == ToolCategory.CONVERSATION

    def test_reasoning_tools_registered(self):
        """Verify reasoning/analysis tools are registered."""
        all_tools = ToolRegistry._tools

        # Check for at least polya_reasoning
        assert "polya_reasoning" in all_tools, "polya_reasoning not registered"
        tool = all_tools["polya_reasoning"]
        # Reasoning tools might be in ANALYSIS category
        assert tool.category in [ToolCategory.ANALYSIS, ToolCategory.MATH]

    def test_tools_by_category(self):
        """Verify tools are organized by category."""
        categories = ToolRegistry._categories

        # Should have at least these categories
        expected_categories = [
            ToolCategory.SEARCH,
            ToolCategory.SYSTEM,
            ToolCategory.MATH,
            ToolCategory.IMAGE,
            ToolCategory.CONVERSATION,
        ]

        for category in expected_categories:
            assert category in categories, f"Category {category} not found"
            assert len(categories[category]) > 0, f"No tools in {category}"

    def test_tool_descriptions_not_empty(self):
        """Verify all tools have non-empty descriptions."""
        all_tools = ToolRegistry._tools

        for tool_name, tool_info in all_tools.items():
            assert (
                tool_info.description
            ), f"Tool {tool_name} has empty description"
            assert (
                len(tool_info.description) > 10
            ), f"Tool {tool_name} description too short"

    def test_search_category_has_web_tools(self):
        """Verify SEARCH category contains web tools."""
        search_tools = ToolRegistry.get_by_category(ToolCategory.SEARCH)

        tool_names = [tool.name for tool in search_tools]

        assert "search_web" in tool_names, "search_web not in SEARCH category"
        assert (
            "scrape_website" in tool_names
        ), "scrape_website not in SEARCH category"

    def test_can_retrieve_tools_by_name(self):
        """Verify tools can be retrieved by name."""
        # Test web tools
        search_tool = ToolRegistry.get("search_web")
        assert search_tool is not None
        assert search_tool.name == "search_web"

        scrape_tool = ToolRegistry.get("scrape_website")
        assert scrape_tool is not None
        assert scrape_tool.name == "scrape_website"

        # Test calendar tools
        create_event_tool = ToolRegistry.get("create_calendar_event")
        assert create_event_tool is not None
        assert create_event_tool.name == "create_calendar_event"

    def test_tool_functions_are_callable(self):
        """Verify registered tool functions are callable."""
        all_tools = ToolRegistry._tools

        for tool_name, tool_info in all_tools.items():
            assert callable(
                tool_info.func
            ), f"Tool {tool_name} func is not callable"

    def test_minimum_tool_count(self):
        """Verify minimum expected number of tools are registered."""
        all_tools = ToolRegistry._tools

        # Should have at least 20 tools registered
        # (web, calendar, math, image, system, conversation, reasoning)
        assert (
            len(all_tools) >= 20
        ), f"Expected at least 20 tools, found {len(all_tools)}"

    def test_no_duplicate_tool_names(self):
        """Verify no duplicate tool names exist."""
        all_tools = ToolRegistry._tools
        tool_names = list(all_tools.keys())

        # Check for duplicates
        unique_names = set(tool_names)
        assert len(tool_names) == len(
            unique_names
        ), "Duplicate tool names found"

    def test_tools_have_valid_metadata(self):
        """Verify all tools have valid metadata."""
        all_tools = ToolRegistry._tools

        for tool_name, tool_info in all_tools.items():
            # Check required fields
            assert tool_info.name, f"Tool {tool_name} missing name"
            assert tool_info.category, f"Tool {tool_name} missing category"
            assert (
                tool_info.description
            ), f"Tool {tool_name} missing description"
            assert tool_info.func, f"Tool {tool_name} missing function"

            # Check boolean flags are actually booleans
            assert isinstance(tool_info.return_direct, bool)
            assert isinstance(tool_info.requires_agent, bool)
            assert isinstance(tool_info.requires_api, bool)


class TestToolAvailability:
    """Test that tools are available and functional."""

    def test_web_search_tool_callable(self):
        """Verify search_web tool can be called."""
        from airunner.components.llm.tools.web_tools import search_web

        # Should be callable
        assert callable(search_web)

    def test_web_scrape_tool_callable(self):
        """Verify scrape_website tool can be called."""
        from airunner.components.llm.tools.web_tools import scrape_website

        # Should be callable
        assert callable(scrape_website)

    def test_calendar_tools_callable(self):
        """Verify calendar tools can be imported and called."""
        from airunner.components.llm.tools.calendar_tools import (
            create_calendar_event,
            list_calendar_events,
            update_calendar_event,
            delete_calendar_event,
        )

        assert callable(create_calendar_event)
        assert callable(list_calendar_events)
        assert callable(update_calendar_event)
        assert callable(delete_calendar_event)

    def test_math_tools_callable(self):
        """Verify math tools can be imported and called."""
        from airunner.components.llm.tools.math_tools import (
            sympy_compute,
            numpy_compute,
            python_compute,
        )

        assert callable(sympy_compute)
        assert callable(numpy_compute)
        assert callable(python_compute)

    def test_image_tools_callable(self):
        """Verify image tools can be imported and called."""
        from airunner.components.llm.tools.image_tools import (
            generate_image,
            set_image_dimensions,
            clear_canvas,
            open_image,
        )

        assert callable(generate_image)
        assert callable(set_image_dimensions)
        assert callable(clear_canvas)
        assert callable(open_image)


if __name__ == "__main__":
    # Allow running directly for quick verification
    pytest.main([__file__, "-v"])
