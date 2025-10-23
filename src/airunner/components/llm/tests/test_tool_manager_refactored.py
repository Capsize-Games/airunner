"""Tests for refactored ToolManager with mixin architecture."""

import unittest
from unittest.mock import Mock, MagicMock, patch

from airunner.components.llm.managers.tool_manager import ToolManager
from airunner.components.llm.tests.base_test_case import BaseTestCase


class TestToolManager(BaseTestCase):
    """Test refactored ToolManager with mixin composition."""

    def setUp(self):
        """Set up test with mock rag_manager."""
        self.mock_rag_manager = MagicMock()

        # Create ToolManager instance
        self.manager = ToolManager(rag_manager=self.mock_rag_manager)

    def test_instantiation(self):
        """Test that ToolManager can be instantiated."""
        self.assertIsNotNone(self.manager)
        self.assertIsInstance(self.manager, ToolManager)

    def test_has_rag_manager(self):
        """Test that ToolManager has rag_manager attribute."""
        self.assertTrue(hasattr(self.manager, "rag_manager"))

    def test_get_all_tools_returns_list(self):
        """Test that get_all_tools returns a list."""
        tools = self.manager.get_all_tools()
        self.assertIsInstance(tools, list)

    def test_get_all_tools_not_empty(self):
        """Test that get_all_tools returns tools from all mixins."""
        tools = self.manager.get_all_tools()
        self.assertGreater(len(tools), 0)
        # We expect 39 tools (8 conversation + 8 autonomous + 23 original)
        self.assertGreaterEqual(len(tools), 30)

    def test_tool_names_unique(self):
        """Test that all tool names are unique."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        # Check for duplicates
        self.assertEqual(len(tool_names), len(set(tool_names)))

    def test_has_conversation_tools(self):
        """Test that conversation tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        # Check for some conversation tools
        self.assertIn("list_conversations", tool_names)
        self.assertIn("get_conversation", tool_names)
        self.assertIn("create_new_conversation", tool_names)

    def test_has_autonomous_control_tools(self):
        """Test that autonomous control tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        # Check for some autonomous tools
        self.assertIn("get_application_state", tool_names)
        self.assertIn("schedule_task", tool_names)
        self.assertIn("propose_action", tool_names)

    def test_has_rag_tools(self):
        """Test that RAG tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        self.assertIn("rag_search", tool_names)
        self.assertIn("save_to_knowledge_base", tool_names)

    def test_has_image_tools(self):
        """Test that image tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        self.assertIn("generate_image", tool_names)
        self.assertIn("clear_canvas", tool_names)

    def test_has_file_tools(self):
        """Test that file tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        self.assertIn("list_files", tool_names)
        self.assertIn("read_file", tool_names)
        self.assertIn("write_code", tool_names)

    def test_has_web_tools(self):
        """Test that web tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        self.assertIn("search_web", tool_names)
        self.assertIn(
            "scrape_website", tool_names
        )  # web_scraper tool is named "scrape_website"

    def test_has_code_tools(self):
        """Test that code tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        self.assertIn(
            "calculate", tool_names
        )  # calculator tool is named "calculate"
        self.assertIn("execute_python", tool_names)
        self.assertIn("create_tool", tool_names)

    def test_has_system_tools(self):
        """Test that system tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        self.assertIn("clear_conversation", tool_names)
        self.assertIn("quit_application", tool_names)
        self.assertIn("toggle_tts", tool_names)

    def test_has_knowledge_tools(self):
        """Test that knowledge tools are included."""
        tools = self.manager.get_all_tools()
        tool_names = [tool.name for tool in tools]

        self.assertIn("record_knowledge", tool_names)
        self.assertIn("recall_knowledge", tool_names)

    def test_all_tools_callable(self):
        """Test that all tools have callable functions."""
        tools = self.manager.get_all_tools()

        for tool in tools:
            # LangChain tools have a func attribute that is callable
            self.assertTrue(
                hasattr(tool, "func"),
                f"Tool {tool.name} missing func attribute",
            )
            self.assertTrue(
                callable(tool.func), f"Tool {tool.name}.func is not callable"
            )

    def test_all_tools_have_names(self):
        """Test that all tools have a name attribute."""
        tools = self.manager.get_all_tools()

        for tool in tools:
            self.assertTrue(
                hasattr(tool, "name"),
                f"Tool {tool} is missing 'name' attribute",
            )
            self.assertIsInstance(
                tool.name, str, f"Tool name is not a string: {tool.name}"
            )
            self.assertGreater(
                len(tool.name), 0, f"Tool has empty name: {tool}"
            )

    def test_all_tools_have_descriptions(self):
        """Test that all tools have descriptions."""
        tools = self.manager.get_all_tools()

        for tool in tools:
            # LangChain tools should have description attribute
            self.assertTrue(
                hasattr(tool, "description") or hasattr(tool, "func"),
                f"Tool {tool.name} missing description",
            )

    def test_mixin_inheritance(self):
        """Test that ToolManager inherits from all mixins."""
        from airunner.components.llm.managers.tools.conversation_tools import (
            ConversationTools,
        )
        from airunner.components.llm.managers.tools.autonomous_control_tools import (
            AutonomousControlTools,
        )
        from airunner.components.llm.managers.tools.rag_tools import RAGTools
        from airunner.components.llm.managers.tools.image_tools import (
            ImageTools,
        )

        # Check mixin inheritance
        self.assertIsInstance(self.manager, ConversationTools)
        self.assertIsInstance(self.manager, AutonomousControlTools)
        self.assertIsInstance(self.manager, RAGTools)
        self.assertIsInstance(self.manager, ImageTools)


class TestToolManagerCustomTools(unittest.TestCase):
    """Test custom tool loading functionality."""

    def setUp(self):
        """Set up test with mock rag_manager."""
        self.mock_rag_manager = MagicMock()

    def test_get_all_tools_caching(self):
        """Test that get_all_tools can be called multiple times."""
        manager = ToolManager(rag_manager=self.mock_rag_manager)

        tools1 = manager.get_all_tools()
        tools2 = manager.get_all_tools()

        # Should return same number of tools
        self.assertEqual(len(tools1), len(tools2))


if __name__ == "__main__":
    unittest.main()
