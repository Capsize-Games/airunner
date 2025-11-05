"""Tests for ConversationTools mixin."""

import unittest
from unittest.mock import Mock
from datetime import datetime

from airunner.components.llm.managers.tools.conversation_tools import (
    ConversationTools,
)
from airunner.components.llm.tests.base_test_case import DatabaseTestCase
from airunner.components.llm.data.conversation import Conversation
from airunner.enums import SignalCode


class MockConversationToolsClass(ConversationTools):
    """Mock class for testing ConversationTools mixin."""

    def __init__(self):
        self.logger = Mock()
        self.emit_signal = Mock()


class TestConversationTools(DatabaseTestCase):
    """Test ConversationTools mixin methods."""

    def setUp(self):
        """Set up test with mock conversation tools instance."""
        super().setUp()
        self.tools = MockConversationToolsClass()

    def test_list_conversations_tool_creation(self):
        """Test that list_conversations_tool creates a callable tool."""
        tool = self.tools.list_conversations_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "list_conversations")

    def test_list_conversations_empty_database(self):
        """Test listing conversations when database is empty."""
        tool = self.tools.list_conversations_tool()
        result = self.invoke_tool(tool, limit=10)
        self.assertIn("No conversations found", result)

    def test_list_conversations_with_data(self):
        """Test listing conversations with existing data."""
        # Create test conversations
        conv1 = self.create_test_record(
            Conversation,
            title="Test Conv 1",
            timestamp=datetime.now(),
            value=[],
            current=False,
        )
        conv2 = self.create_test_record(
            Conversation,
            title="Test Conv 2",
            timestamp=datetime.now(),
            value=[],
            current=True,
        )

        tool = self.tools.list_conversations_tool()
        result = self.invoke_tool(tool, limit=10)

        self.assertIn("Found 2 conversations", result)
        self.assertIn("Test Conv 1", result)
        self.assertIn("Test Conv 2", result)
        self.assertIn("* (CURRENT)", result)

    def test_get_conversation_tool_creation(self):
        """Test that get_conversation_tool creates a callable tool."""
        tool = self.tools.get_conversation_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "get_conversation")

    def test_get_conversation_not_found(self):
        """Test getting a non-existent conversation."""
        tool = self.tools.get_conversation_tool()
        result = self.invoke_tool(tool, conversation_id=99999)
        self.assertIn("not found", result.lower())

    def test_get_conversation_with_messages(self):
        """Test getting conversation with messages included."""
        # Create test conversation with messages
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        conv = self.create_test_record(
            Conversation,
            title="Test Conv",
            timestamp=datetime.now(),
            value=messages,
            current=False,
        )

        tool = self.tools.get_conversation_tool()
        result = self.invoke_tool(tool, conversation_id=conv.id, include_messages=True)

        self.assertIn("Test Conv", result)
        self.assertIn("2 messages", result)
        self.assertIn("Hello", result)
        self.assertIn("Hi there!", result)

    def test_summarize_conversation_tool_creation(self):
        """Test that summarize_conversation_tool creates a callable tool."""
        tool = self.tools.summarize_conversation_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "summarize_conversation")

    def test_update_conversation_title_tool_creation(self):
        """Test that update_conversation_title_tool creates a callable tool."""
        tool = self.tools.update_conversation_title_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "update_conversation_title")

    def test_update_conversation_title_success(self):
        """Test updating conversation title successfully."""
        conv = self.create_test_record(
            Conversation,
            title="Old Title",
            timestamp=datetime.now(),
            value=[],
            current=False,
        )

        tool = self.tools.update_conversation_title_tool()
        result = self.invoke_tool(tool, conversation_id=conv.id, new_title="New Title")

        self.assertIn("Updated title", result)
        self.assertIn("New Title", result)

        # Verify signal was emitted
        self.tools.emit_signal.assert_called_with(
            SignalCode.CONVERSATION_TITLE_UPDATED,
            {"conversation_id": conv.id, "new_title": "New Title"},
        )

    def test_switch_conversation_tool_creation(self):
        """Test that switch_conversation_tool creates a callable tool."""
        tool = self.tools.switch_conversation_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "switch_conversation")

    def test_switch_conversation_success(self):
        """Test switching to a different conversation."""
        conv = self.create_test_record(
            Conversation,
            title="Target Conv",
            timestamp=datetime.now(),
            value=[],
            current=False,
        )

        tool = self.tools.switch_conversation_tool()
        result = self.invoke_tool(tool, conversation_id=conv.id)

        self.assertIn("Switched to conversation", result)

        # Verify signal was emitted
        self.tools.emit_signal.assert_called_with(
            SignalCode.LOAD_CONVERSATION_SIGNAL, {"conversation_id": conv.id}
        )

    def test_create_new_conversation_tool_creation(self):
        """Test that create_new_conversation_tool creates a callable tool."""
        tool = self.tools.create_new_conversation_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "create_new_conversation")

    def test_create_new_conversation_with_title(self):
        """Test creating new conversation with custom title."""
        tool = self.tools.create_new_conversation_tool()
        result = self.invoke_tool(tool, title="My New Conversation")

        self.assertIn("Created new conversation", result)
        self.assertIn("My New Conversation", result)

        # Verify signal was emitted
        self.tools.emit_signal.assert_called()
        call_args = self.tools.emit_signal.call_args
        self.assertEqual(call_args[0][0], SignalCode.NEW_CONVERSATION_SIGNAL)

    def test_search_conversations_tool_creation(self):
        """Test that search_conversations_tool creates a callable tool."""
        tool = self.tools.search_conversations_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "search_conversations")

    def test_search_conversations_by_title(self):
        """Test searching conversations by title."""
        conv1 = self.create_test_record(
            Conversation,
            title="Python Tutorial",
            timestamp=datetime.now(),
            value=[],
            current=False,
        )
        conv2 = self.create_test_record(
            Conversation,
            title="JavaScript Guide",
            timestamp=datetime.now(),
            value=[],
            current=False,
        )

        tool = self.tools.search_conversations_tool()
        result = self.invoke_tool(tool, query="Python", limit=10)

        self.assertIn("Python Tutorial", result)
        self.assertNotIn("JavaScript", result)

    def test_delete_conversation_tool_creation(self):
        """Test that delete_conversation_tool creates a callable tool."""
        tool = self.tools.delete_conversation_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "delete_conversation")

    def test_delete_conversation_requires_confirmation(self):
        """Test that delete requires confirmation."""
        conv = self.create_test_record(
            Conversation,
            title="To Delete",
            timestamp=datetime.now(),
            value=[],
            current=False,
        )

        tool = self.tools.delete_conversation_tool()
        result = self.invoke_tool(tool, conversation_id=conv.id, confirm=False)

        self.assertIn("WARNING", result)
        self.assertIn("confirm=True", result)

        # Verify conversation still exists
        self.assertEqual(self.count_records(Conversation), 1)

    def test_delete_conversation_prevents_current(self):
        """Test that cannot delete current conversation."""
        conv = self.create_test_record(
            Conversation,
            title="Current Conv",
            timestamp=datetime.now(),
            value=[],
            current=True,
        )

        tool = self.tools.delete_conversation_tool()
        result = self.invoke_tool(tool, conversation_id=conv.id, confirm=True)

        self.assertIn("Cannot delete the current active conversation", result)


if __name__ == "__main__":
    unittest.main()
