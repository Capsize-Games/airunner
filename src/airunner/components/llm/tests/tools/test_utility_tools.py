"""Tests for WebTools, CodeTools, SystemTools, and UserDataTools mixins."""

import unittest
from unittest.mock import Mock, MagicMock, patch
import json

from airunner.components.llm.managers.tools.web_tools import WebTools
from airunner.components.llm.managers.tools.code_tools import CodeTools
from airunner.components.llm.managers.tools.system_tools import SystemTools
from airunner.components.llm.managers.tools.user_data_tools import (
    UserDataTools,
)
from airunner.components.llm.tests.base_test_case import (
    BaseTestCase,
    DatabaseTestCase,
)
from airunner.enums import SignalCode


class MockWebToolsClass(WebTools):
    """Mock class for testing WebTools mixin."""

    def __init__(self):
        self.logger = Mock()


class MockCodeToolsClass(CodeTools):
    """Mock class for testing CodeTools mixin."""

    def __init__(self):
        self.logger = Mock()


class MockSystemToolsClass(SystemTools):
    """Mock class for testing SystemTools mixin."""

    def __init__(self):
        self.logger = Mock()
        self.emit_signal = Mock()


class MockUserDataToolsClass(UserDataTools):
    """Mock class for testing UserDataTools mixin."""

    def __init__(self):
        self.logger = Mock()


class TestWebTools(BaseTestCase):
    """Test WebTools mixin methods."""

    def setUp(self):
        """Set up test with mock web tools instance."""
        self.tools = MockWebToolsClass()

    def test_search_web_tool_creation(self):
        """Test that search_web_tool creates a callable tool."""
        tool = self.tools.search_web_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "search_web")

    @patch("requests.get")
    def test_search_web_success(self, mock_get):
        """Test web search with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Search results for test query"
        mock_get.return_value = mock_response

        tool = self.tools.search_web_tool()
        result = tool(query="test query")

        self.assertIn("Search results", result)

    def test_web_scraper_tool_creation(self):
        """Test that web_scraper_tool creates a callable tool."""
        tool = self.tools.web_scraper_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "web_scraper")

    @patch("requests.get")
    def test_web_scraper_success(self, mock_get):
        """Test web scraping with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = (
            "<html><body><h1>Title</h1><p>Content</p></body></html>"
        )
        mock_get.return_value = mock_response

        tool = self.tools.web_scraper_tool()
        result = tool(url="https://example.com")

        self.assertIn("Title", result)
        self.assertIn("Content", result)


class TestCodeTools(BaseTestCase):
    """Test CodeTools mixin methods."""

    def setUp(self):
        """Set up test with mock code tools instance."""
        self.tools = MockCodeToolsClass()

    def test_calculator_tool_creation(self):
        """Test that calculator_tool creates a callable tool."""
        tool = self.tools.calculator_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "calculator")

    def test_calculator_simple_math(self):
        """Test calculator with simple math expressions."""
        tool = self.tools.calculator_tool()

        # Addition
        result = tool(expression="2 + 2")
        self.assertIn("4", result)

        # Multiplication
        result = tool(expression="5 * 6")
        self.assertIn("30", result)

        # Complex expression
        result = tool(expression="(10 + 5) * 2")
        self.assertIn("30", result)

    def test_calculator_with_functions(self):
        """Test calculator with math functions."""
        tool = self.tools.calculator_tool()

        result = tool(expression="sqrt(16)")
        self.assertIn("4", result)

        result = tool(expression="sin(0)")
        self.assertIn("0", result)

    def test_calculator_invalid_expression(self):
        """Test calculator with invalid expression."""
        tool = self.tools.calculator_tool()
        result = tool(expression="invalid / code")

        self.assertIn("Error", result)

    def test_execute_python_tool_creation(self):
        """Test that execute_python_tool creates a callable tool."""
        tool = self.tools.execute_python_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "execute_python")

    def test_execute_python_simple_code(self):
        """Test executing simple Python code."""
        tool = self.tools.execute_python_tool()
        result = tool(code="print('Hello, World!')")

        self.assertIn("Hello, World!", result)

    def test_execute_python_with_return_value(self):
        """Test executing Python code with return value."""
        tool = self.tools.execute_python_tool()
        result = tool(code="x = 10\ny = 20\nprint(x + y)")

        self.assertIn("30", result)

    def test_execute_python_with_error(self):
        """Test executing Python code with syntax error."""
        tool = self.tools.execute_python_tool()
        result = tool(code="invalid python syntax !!!")

        self.assertIn("Error", result)

    def test_create_tool_tool_creation(self):
        """Test that create_tool_tool creates a callable tool."""
        tool = self.tools.create_tool_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "create_tool")


class TestSystemTools(BaseTestCase):
    """Test SystemTools mixin methods."""

    def setUp(self):
        """Set up test with mock system tools instance."""
        self.tools = MockSystemToolsClass()

    def test_clear_conversation_tool_creation(self):
        """Test that clear_conversation_tool creates a callable tool."""
        tool = self.tools.clear_conversation_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "clear_conversation")

    def test_clear_conversation_emits_signal(self):
        """Test that clear_conversation emits the correct signal."""
        tool = self.tools.clear_conversation_tool()
        result = tool()

        self.assertIn("Cleared conversation", result)
        self.tools.emit_signal.assert_called_with(
            SignalCode.CLEAR_CONVERSATION_SIGNAL
        )

    def test_quit_application_tool_creation(self):
        """Test that quit_application_tool creates a callable tool."""
        tool = self.tools.quit_application_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "quit_application")

    def test_quit_application_emits_signal(self):
        """Test that quit_application emits the correct signal."""
        tool = self.tools.quit_application_tool()
        result = tool()

        self.assertIn("Quitting application", result)
        self.tools.emit_signal.assert_called_with(
            SignalCode.APPLICATION_QUIT_SIGNAL
        )

    def test_toggle_tts_tool_creation(self):
        """Test that toggle_tts_tool creates a callable tool."""
        tool = self.tools.toggle_tts_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "toggle_tts")

    def test_toggle_tts_on(self):
        """Test toggling TTS on."""
        tool = self.tools.toggle_tts_tool()
        result = tool(enabled=True)

        self.assertIn("TTS enabled", result)
        self.tools.emit_signal.assert_called_with(
            SignalCode.TOGGLE_TTS_SIGNAL, {"enabled": True}
        )

    def test_toggle_tts_off(self):
        """Test toggling TTS off."""
        tool = self.tools.toggle_tts_tool()
        result = tool(enabled=False)

        self.assertIn("TTS disabled", result)
        self.tools.emit_signal.assert_called_with(
            SignalCode.TOGGLE_TTS_SIGNAL, {"enabled": False}
        )

    def test_update_mood_tool_creation(self):
        """Test that update_mood_tool creates a callable tool."""
        tool = self.tools.update_mood_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "update_mood")

    def test_update_mood_emits_signal(self):
        """Test that update_mood emits the correct signal."""
        tool = self.tools.update_mood_tool()
        result = tool(mood="happy")

        self.assertIn("Updated mood", result)
        self.tools.emit_signal.assert_called_with(
            SignalCode.UPDATE_MOOD_SIGNAL, {"mood": "happy"}
        )

    def test_emit_signal_tool_creation(self):
        """Test that emit_signal_tool creates a callable tool."""
        tool = self.tools.emit_signal_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "emit_signal")

    def test_emit_signal_with_data(self):
        """Test emitting signal with data."""
        tool = self.tools.emit_signal_tool()
        data = {"key": "value", "number": 42}
        result = tool(signal_code="CUSTOM_SIGNAL", data=data)

        self.assertIn("Emitted signal", result)
        # Note: emit_signal is called twice - once in the tool, once for logging
        self.assertEqual(self.tools.emit_signal.call_count, 2)


class TestUserDataTools(DatabaseTestCase):
    """Test UserDataTools mixin methods."""

    def setUp(self):
        """Set up test with mock user data tools instance."""
        super().setUp()
        self.tools = MockUserDataToolsClass()

    def test_store_user_data_tool_creation(self):
        """Test that store_user_data_tool creates a callable tool."""
        tool = self.tools.store_user_data_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "store_user_data")

    def test_get_user_data_tool_creation(self):
        """Test that get_user_data_tool creates a callable tool."""
        tool = self.tools.get_user_data_tool()
        self.assertIsNotNone(tool)
        self.assertTrue(callable(tool))
        self.assertEqual(tool.name, "get_user_data")


if __name__ == "__main__":
    unittest.main()
