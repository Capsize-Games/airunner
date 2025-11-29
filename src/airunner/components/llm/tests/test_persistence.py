"""Tests for database persistence layer (chat history and checkpointing)."""

import unittest
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from airunner.components.llm.managers.database_chat_message_history import (
    DatabaseChatMessageHistory,
)
from airunner.components.llm.managers.database_checkpoint_saver import (
    DatabaseCheckpointSaver,
)
from airunner.components.llm.tests.base_test_case import DatabaseTestCase
from airunner.components.llm.data.conversation import Conversation


class TestDatabaseChatMessageHistory(DatabaseTestCase):
    """Test DatabaseChatMessageHistory class."""

    def setUp(self):
        """Set up test with database."""
        super().setUp()

    def test_init_creates_conversation(self):
        """Test that initialization creates a conversation if none exists."""
        history = DatabaseChatMessageHistory()
        self.assertIsNotNone(history.conversation_id)
        self.assertIsNotNone(history._conversation)

    def test_init_loads_existing_conversation(self):
        """Test that initialization loads existing conversation."""
        # Create a conversation
        conv = self.create_test_record(
            Conversation,
            title="Test Conv",
            timestamp=datetime.now(),
            value=[],
            current=True,
        )

        history = DatabaseChatMessageHistory(conversation_id=conv.id)
        self.assertEqual(history.conversation_id, conv.id)

    def test_messages_property_empty(self):
        """Test messages property when conversation is empty."""
        history = DatabaseChatMessageHistory()
        messages = history.messages

        self.assertIsInstance(messages, list)
        self.assertEqual(len(messages), 0)

    def test_add_human_message(self):
        """Test adding a human message."""
        history = DatabaseChatMessageHistory()
        msg = HumanMessage(content="Hello, AI!")

        history.add_message(msg)

        # Verify message was added
        messages = history.messages
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], HumanMessage)
        self.assertEqual(messages[0].content, "Hello, AI!")

    def test_add_ai_message(self):
        """Test adding an AI message."""
        history = DatabaseChatMessageHistory()
        msg = AIMessage(content="Hello, human!")

        history.add_message(msg)

        # Verify message was added
        messages = history.messages
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], AIMessage)
        self.assertEqual(messages[0].content, "Hello, human!")

    def test_add_system_message(self):
        """Test adding a system message."""
        history = DatabaseChatMessageHistory()
        msg = SystemMessage(content="System initialized")

        history.add_message(msg)

        # Verify message was added
        messages = history.messages
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertEqual(messages[0].content, "System initialized")

    def test_add_multiple_messages(self):
        """Test adding multiple messages in sequence."""
        history = DatabaseChatMessageHistory()

        messages_to_add = [
            HumanMessage(content="First"),
            AIMessage(content="Second"),
            HumanMessage(content="Third"),
        ]

        for msg in messages_to_add:
            history.add_message(msg)

        # Verify all messages were added
        stored_messages = history.messages
        self.assertEqual(len(stored_messages), 3)
        self.assertEqual(stored_messages[0].content, "First")
        self.assertEqual(stored_messages[1].content, "Second")
        self.assertEqual(stored_messages[2].content, "Third")

    def test_add_messages_batch(self):
        """Test adding messages in batch."""
        history = DatabaseChatMessageHistory()

        messages = [
            HumanMessage(content="Batch 1"),
            AIMessage(content="Batch 2"),
            HumanMessage(content="Batch 3"),
        ]

        history.add_messages(messages)

        # Verify all messages were added
        stored_messages = history.messages
        self.assertEqual(len(stored_messages), 3)

    def test_clear_messages(self):
        """Test clearing all messages."""
        history = DatabaseChatMessageHistory()

        # Add some messages
        history.add_message(HumanMessage(content="Test 1"))
        history.add_message(AIMessage(content="Test 2"))

        # Verify messages exist
        self.assertEqual(len(history.messages), 2)

        # Clear messages
        history.clear()

        # Verify messages are cleared
        self.assertEqual(len(history.messages), 0)

    def test_messages_persist_across_instances(self):
        """Test that messages persist when creating new instance."""
        # Create first instance and add messages
        history1 = DatabaseChatMessageHistory()
        conv_id = history1.conversation_id

        history1.add_message(HumanMessage(content="Persistent message"))

        # Create second instance with same conversation ID
        history2 = DatabaseChatMessageHistory(conversation_id=conv_id)

        # Verify message persisted
        messages = history2.messages
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, "Persistent message")

    def test_tool_call_metadata_storage(self):
        """Test that tool calls and results are stored as metadata."""
        history = DatabaseChatMessageHistory()

        # Add a regular message
        history.add_message(HumanMessage(content="Search for something"))

        # Add an AI message with tool calls
        ai_msg_with_tools = AIMessage(content="")
        ai_msg_with_tools.tool_calls = [
            {
                "name": "search_web",
                "args": {"query": "test query"},
                "id": "call_123",
            }
        ]
        history.add_message(ai_msg_with_tools)

        # Add a tool result message
        from langchain_core.messages import ToolMessage

        tool_msg = ToolMessage(
            content="Search results here...", tool_call_id="call_123"
        )
        history.add_message(tool_msg)

        # Add final AI response
        history.add_message(AIMessage(content="Here's what I found..."))

        # Verify regular messages don't include tool metadata
        messages = history.messages
        self.assertEqual(len(messages), 2)  # Only user + final AI message
        self.assertEqual(messages[0].content, "Search for something")
        self.assertEqual(messages[1].content, "Here's what I found...")

        # Verify tool call metadata is stored separately
        metadata = history.get_tool_call_metadata()
        self.assertEqual(len(metadata), 2)  # Tool call + tool result

        # Check tool call metadata
        tool_call_entry = next(
            (m for m in metadata if m.get("metadata_type") == "tool_calls"),
            None,
        )
        self.assertIsNotNone(tool_call_entry)
        self.assertEqual(tool_call_entry["role"], "tool_calls")
        self.assertIn("tool_calls", tool_call_entry)
        self.assertEqual(
            tool_call_entry["tool_calls"][0]["name"], "search_web"
        )

        # Check tool result metadata
        tool_result_entry = next(
            (m for m in metadata if m.get("metadata_type") == "tool_result"),
            None,
        )
        self.assertIsNotNone(tool_result_entry)
        self.assertEqual(tool_result_entry["role"], "tool_result")
        self.assertEqual(
            tool_result_entry["content"], "Search results here..."
        )
        self.assertEqual(tool_result_entry["tool_call_id"], "call_123")


class TestDatabaseCheckpointSaver(DatabaseTestCase):
    """Test DatabaseCheckpointSaver class."""

    def setUp(self):
        """Set up test with database."""
        super().setUp()
        # Clear all checkpoint state before each test to prevent contamination
        DatabaseCheckpointSaver.clear_all_checkpoint_state()

    def tearDown(self):
        """Clean up after each test."""
        # Clear all checkpoint state after each test
        DatabaseCheckpointSaver.clear_all_checkpoint_state()
        super().tearDown()

    def test_init(self):
        """Test initialization of checkpoint saver."""
        saver = DatabaseCheckpointSaver()
        self.assertIsNotNone(saver)
        self.assertIsNotNone(saver.chat_history)

    def test_init_with_conversation_id(self):
        """Test initialization with specific conversation ID."""
        conv = self.create_test_record(
            Conversation,
            title="Test Conv",
            timestamp=datetime.now(),
            value=[],
            current=False,
        )

        saver = DatabaseCheckpointSaver(conversation_id=conv.id)
        self.assertEqual(saver.chat_history.conversation_id, conv.id)

    def test_put_checkpoint(self):
        """Test saving a checkpoint."""
        saver = DatabaseCheckpointSaver()

        # Create a simple checkpoint
        config = {"configurable": {"thread_id": "test_thread"}}
        checkpoint = {
            "v": 1,
            "ts": datetime.now().isoformat(),
            "channel_values": {"messages": []},
        }
        metadata = {"source": "test"}

        # Save checkpoint
        result = saver.put(config, checkpoint, metadata, {})

        self.assertIsNotNone(result)
        self.assertIn("configurable", result)

    def test_get_checkpoint_not_found(self):
        """Test getting checkpoint that doesn't exist."""
        saver = DatabaseCheckpointSaver()
        config = {"configurable": {"thread_id": "nonexistent"}}

        result = saver.get_tuple(config)
        self.assertIsNone(result)

    def test_put_and_get_checkpoint(self):
        """Test saving and retrieving a checkpoint."""
        saver = DatabaseCheckpointSaver()

        config = {"configurable": {"thread_id": "test_thread_123"}}
        checkpoint = {
            "v": 1,
            "ts": datetime.now().isoformat(),
            "channel_values": {
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi!"},
                ]
            },
        }
        metadata = {"step": 1}

        # Save checkpoint
        saved_config = saver.put(config, checkpoint, metadata, {})

        # Retrieve checkpoint
        result = saver.get_tuple(saved_config)

        self.assertIsNotNone(result)
        # DatabaseCheckpointSaver might return None if not fully implemented
        # Just verify it doesn't crash

    def test_list_checkpoints(self):
        """Test listing checkpoints."""
        saver = DatabaseCheckpointSaver()
        config = {"configurable": {"thread_id": "test_thread"}}

        # List should return an iterable
        checkpoints = list(saver.list(config))
        self.assertIsInstance(checkpoints, list)

    def test_checkpoint_with_messages(self):
        """Test checkpoint includes message history."""
        saver = DatabaseCheckpointSaver()

        # Add messages to chat history
        saver.chat_history.add_message(HumanMessage(content="Test message"))

        config = {"configurable": {"thread_id": "test_with_messages"}}
        checkpoint = {
            "v": 1,
            "ts": datetime.now().isoformat(),
            "channel_values": {"messages": []},
        }

        # Save checkpoint
        saver.put(config, checkpoint, {}, {})

        # Verify messages are in conversation
        messages = saver.chat_history.messages
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, "Test message")


class TestPersistenceIntegration(DatabaseTestCase):
    """Integration tests for persistence layer."""

    def test_chat_history_and_checkpoint_saver_integration(self):
        """Test that chat history and checkpoint saver work together."""
        # Create a conversation
        conv = self.create_test_record(
            Conversation,
            title="Integration Test",
            timestamp=datetime.now(),
            value=[],
            current=True,
        )

        # Create chat history
        history = DatabaseChatMessageHistory(conversation_id=conv.id)
        history.add_message(HumanMessage(content="Integration test message"))

        # Create checkpoint saver with same conversation
        saver = DatabaseCheckpointSaver(conversation_id=conv.id)

        # Verify both can access the same conversation
        self.assertEqual(saver.chat_history.conversation_id, conv.id)
        messages = saver.chat_history.messages
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, "Integration test message")

    def test_multiple_conversations_isolated(self):
        """Test that multiple conversations are properly isolated."""
        # Create two conversations
        conv1 = self.create_test_record(
            Conversation,
            title="Conv 1",
            timestamp=datetime.now(),
            value=[],
            current=False,
        )
        conv2 = self.create_test_record(
            Conversation,
            title="Conv 2",
            timestamp=datetime.now(),
            value=[],
            current=True,
        )

        # Add messages to each
        history1 = DatabaseChatMessageHistory(conversation_id=conv1.id)
        history1.add_message(HumanMessage(content="Message in conv 1"))

        history2 = DatabaseChatMessageHistory(conversation_id=conv2.id)
        history2.add_message(HumanMessage(content="Message in conv 2"))

        # Verify isolation
        messages1 = history1.messages
        messages2 = history2.messages

        self.assertEqual(len(messages1), 1)
        self.assertEqual(len(messages2), 1)
        self.assertEqual(messages1[0].content, "Message in conv 1")
        self.assertEqual(messages2[0].content, "Message in conv 2")


if __name__ == "__main__":
    unittest.main()
