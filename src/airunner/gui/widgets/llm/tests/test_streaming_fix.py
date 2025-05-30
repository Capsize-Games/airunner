#!/usr/bin/env python3
"""
Test to validate that the streaming fixes work correctly for multiple conversations.
This test verifies that:
1. New conversations create new message widgets
2. Streaming continues to existing widgets properly
3. Message IDs are assigned correctly
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from airunner.gui.widgets.llm.chat_prompt_widget import ChatPromptWidget
from airunner.gui.widgets.llm.message_widget import MessageWidget
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.workers.llm_response_worker import LLMResponseWorker


@pytest.fixture
def mock_app():
    """Create a mock application."""
    app = MagicMock()
    app.llm = MagicMock()
    app.llm.clear_history = MagicMock()
    return app


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.username = "testuser"
    return user


@pytest.fixture
def mock_chatbot():
    """Create a mock chatbot."""
    chatbot = MagicMock()
    chatbot.botname = "testbot"
    return chatbot


@pytest.fixture
def chat_widget(qtbot, mock_app, mock_user, mock_chatbot):
    """Create a chat prompt widget for testing."""
    with patch("sys.exit"), patch(
        "PySide6.QtWidgets.QApplication.exec", return_value=None
    ), patch(
        "airunner.gui.widgets.llm.chat_prompt_widget.ConversationHistoryManager"
    ) as MockChm, patch(
        "airunner.gui.widgets.llm.chat_prompt_widget.create_worker"
    ) as mock_create_worker:
        mock_chm_instance = MockChm.return_value
        mock_response_worker = MagicMock()
        mock_create_worker.return_value = mock_response_worker

        widget = ChatPromptWidget()
        widget._conversation_history_manager = mock_chm_instance
        widget.api = mock_app

        # Mock the properties using PropertyMock
        mock_logger = MagicMock()
        type(widget).logger = PropertyMock(return_value=mock_logger)
        type(widget).user = PropertyMock(return_value=mock_user)
        type(widget).chatbot = PropertyMock(return_value=mock_chatbot)

        # Mock the conversation
        mock_conversation = MagicMock()
        mock_conversation.value = []
        mock_conversation.id = 1
        widget._conversation = mock_conversation
        widget._conversation_id = 1

        qtbot.addWidget(widget)
        return widget
        widget._conversation = mock_conversation
        widget._conversation_id = 1

        qtbot.addWidget(widget)
        return widget


class TestStreamingFix:
    """Test class for streaming fix validation."""

    def test_new_conversation_creates_new_widget(self, qtbot, chat_widget):
        """Test that a new conversation creates a new message widget."""
        # Simulate starting a new conversation
        chat_widget.token_buffer = ["Hello "]

        # Call flush_token_buffer - should create a new widget since none exists
        chat_widget.flush_token_buffer()

        # Check that a widget was created
        layout = chat_widget.ui.scrollAreaWidgetContents.layout()
        widgets = [
            layout.itemAt(i).widget()
            for i in range(layout.count())
            if layout.itemAt(i)
            and isinstance(layout.itemAt(i).widget(), MessageWidget)
        ]

        assert (
            len(widgets) == 1
        ), "Should have created exactly one message widget"

        # The widget should have message_id=None (indicating streaming)
        first_widget = widgets[0]
        assert (
            first_widget.message_id is None
        ), "Streaming widget should have message_id=None"
        assert first_widget.is_bot is True, "Should be a bot message"

    def test_streaming_continues_to_existing_widget(self, qtbot, chat_widget):
        """Test that streaming continues to the existing widget instead of creating new ones."""
        # First, create a streaming widget
        chat_widget.token_buffer = ["Hello "]
        chat_widget.flush_token_buffer()

        layout = chat_widget.ui.scrollAreaWidgetContents.layout()
        initial_count = len(
            [
                layout.itemAt(i).widget()
                for i in range(layout.count())
                if layout.itemAt(i)
                and isinstance(layout.itemAt(i).widget(), MessageWidget)
            ]
        )

        # Now add more tokens - should continue to same widget
        chat_widget.token_buffer = ["world!"]
        chat_widget.flush_token_buffer()

        # Check that no new widgets were created
        final_count = len(
            [
                layout.itemAt(i).widget()
                for i in range(layout.count())
                if layout.itemAt(i)
                and isinstance(layout.itemAt(i).widget(), MessageWidget)
            ]
        )

        assert (
            final_count == initial_count
        ), "Should not create new widgets during streaming"

    def test_second_conversation_creates_new_widget(self, qtbot, chat_widget):
        """Test that a second conversation creates a new widget instead of appending to the first."""
        # First conversation
        chat_widget.token_buffer = ["First conversation"]
        chat_widget.flush_token_buffer()

        # Complete the first conversation by assigning a message ID
        layout = chat_widget.ui.scrollAreaWidgetContents.layout()
        first_widget = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and isinstance(item.widget(), MessageWidget):
                first_widget = item.widget()
                break

        assert first_widget is not None, "Should have found the first widget"

        # Simulate conversation completion by assigning message ID
        first_widget.message_id = 1

        # Start second conversation
        chat_widget.token_buffer = ["Second conversation"]
        chat_widget.flush_token_buffer()

        # Should now have two widgets
        widgets = [
            layout.itemAt(i).widget()
            for i in range(layout.count())
            if layout.itemAt(i)
            and isinstance(layout.itemAt(i).widget(), MessageWidget)
        ]

        assert (
            len(widgets) == 2
        ), "Should have created a second widget for new conversation"

        # First widget should have message_id=1, second should have message_id=None (streaming)
        assert (
            widgets[0].message_id == 1
        ), "First widget should have completed message ID"
        assert (
            widgets[1].message_id is None
        ), "Second widget should be streaming (message_id=None)"

    def test_message_id_assignment_logic(self, qtbot, chat_widget):
        """Test that message IDs are assigned correctly."""
        # Create a widget with explicit message_id=None (streaming)
        widget = chat_widget.add_message_to_conversation(
            name="testbot",
            message="Test message",
            is_bot=True,
            first_message=True,
            _message_id=None,  # Explicitly set to None for streaming
        )

        assert widget is not None, "Widget should be created"
        assert (
            widget.message_id is None
        ), "Widget should have message_id=None for streaming"

    def test_flush_token_buffer_error_handling(self, qtbot, chat_widget):
        """Test that flush_token_buffer handles errors gracefully."""
        # Add some tokens
        chat_widget.token_buffer = ["Test"]

        # Mock an error in the streaming logic
        with patch.object(
            chat_widget,
            "add_message_to_conversation",
            side_effect=Exception("Test error"),
        ):
            # Should not crash
            chat_widget.flush_token_buffer()

            # Buffer should be cleared to prevent getting stuck
            assert (
                len(chat_widget.token_buffer) == 0
            ), "Token buffer should be cleared after error"
