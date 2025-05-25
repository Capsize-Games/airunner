"""
Integration test to verify DetachedInstanceError is resolved in LLM history widgets.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from sqlalchemy.orm.exc import DetachedInstanceError

from airunner.gui.widgets.llm.llm_history_widget import LLMHistoryWidget
from airunner.gui.widgets.llm.llm_history_item_widget import (
    LLMHistoryItemWidget,
)


@pytest.fixture
def mock_detached_conversation():
    """Create a mock conversation that throws DetachedInstanceError on property access."""
    mock_convo = MagicMock()
    mock_convo.id = 1

    # Simulate DetachedInstanceError when accessing lazy-loaded properties
    mock_convo.summarize.side_effect = DetachedInstanceError(
        "Instance is not bound to a Session"
    )
    mock_convo.chatbot_id = 1  # This should work

    # Make timestamp property throw DetachedInstanceError when accessed
    type(mock_convo).timestamp = PropertyMock(
        side_effect=DetachedInstanceError("Instance is not bound to a Session")
    )

    return mock_convo


@pytest.fixture
def mock_attached_conversation():
    """Create a mock conversation that works normally."""
    mock_convo = MagicMock()
    mock_convo.id = 2
    mock_convo.timestamp = "2025-05-24 12:01:00"
    mock_convo.summarize.return_value = "This is a test conversation summary"
    mock_convo.chatbot_id = 1

    return mock_convo


def test_history_widget_handles_detached_conversations(
    qtbot, mock_detached_conversation, mock_attached_conversation
):
    """Test that the history widget gracefully handles DetachedInstanceError scenarios."""

    with patch(
        "airunner.data.models.Conversation.objects.filter"
    ) as mock_filter:
        # Mix detached and attached conversations to test robustness
        mock_filter.return_value = [
            mock_detached_conversation,
            mock_attached_conversation,
        ]

        widget = LLMHistoryWidget()
        qtbot.addWidget(widget)
        widget.show()

        # The widget should load without crashing
        widget.load_conversations()

        # Should have created widgets for both conversations
        layout = widget.ui.gridLayout_2
        conversation_widgets = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() and isinstance(
                item.widget(), LLMHistoryItemWidget
            ):
                conversation_widgets.append(item.widget())

        # Should have 2 conversation widgets (both detached and attached)
        assert len(conversation_widgets) == 2

        # Verify the widgets are properly sorted by ID (descending)
        ids = [widget.conversation.id for widget in conversation_widgets]
        assert ids == [2, 1]  # Should be sorted in descending order


def test_history_item_widget_handles_detached_instance_gracefully(
    qtbot, mock_detached_conversation
):
    """Test that individual history item widgets handle DetachedInstanceError gracefully."""

    # Mock the get_chatbot_by_id method before widget creation
    mock_chatbot = MagicMock()
    mock_chatbot.name = "Test Bot"

    with patch.object(
        LLMHistoryItemWidget, "get_chatbot_by_id", return_value=mock_chatbot
    ):
        # Create the widget with a detached conversation
        widget = LLMHistoryItemWidget(conversation=mock_detached_conversation)
        qtbot.addWidget(widget)
        widget.show()

        # The widget should display fallback text instead of crashing
        conversation_description = widget.ui.conversation_description
        assert (
            "[Conversation unavailable]"
            in conversation_description.toPlainText()
        )

        # Also check that botname and timestamp show fallback values
        botname_label = widget.ui.botname
        assert (
            "Test Bot" in botname_label.text()
        )  # Should show the mocked chatbot name

        timestamp_label = widget.ui.timestamp
        assert (
            "[unavailable]" in timestamp_label.text()
        )  # Should show fallback for detached timestamp


def test_history_widget_handles_empty_filter_result(qtbot):
    """Test that the widget handles empty conversation list gracefully."""

    with patch(
        "airunner.data.models.Conversation.objects.filter"
    ) as mock_filter:
        mock_filter.return_value = []

        widget = LLMHistoryWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.load_conversations()

        # Should have only the spacer item in the layout
        layout = widget.ui.gridLayout_2
        assert layout.count() <= 1  # Only spacer or empty


def test_history_widget_conversation_sorting():
    """Test that conversations are properly sorted by ID descending."""

    # Create conversations with different IDs
    convos = []
    for i in [3, 1, 5, 2, 4]:
        mock_convo = MagicMock()
        mock_convo.id = i
        mock_convo.summarize.return_value = f"Summary {i}"
        mock_convo.chatbot_id = 1
        mock_convo.timestamp = f"2025-05-24 12:0{i}:00"
        convos.append(mock_convo)

    with patch(
        "airunner.data.models.Conversation.objects.filter"
    ) as mock_filter:
        mock_filter.return_value = convos

        widget = LLMHistoryWidget()
        widget.load_conversations()

        # Verify conversations are sorted by ID descending
        layout = widget.ui.gridLayout_2
        conversation_widgets = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() and isinstance(
                item.widget(), LLMHistoryItemWidget
            ):
                conversation_widgets.append(item.widget())

        # Should be sorted [5, 4, 3, 2, 1]
        ids = [widget.conversation.id for widget in conversation_widgets]
        assert ids == [5, 4, 3, 2, 1]


def test_filter_query_avoids_session_boundary_issues():
    """Test that using filter() instead of order_by().all() avoids session issues."""

    # This test verifies that we're not chaining methods across session boundaries
    with patch(
        "airunner.data.models.Conversation.objects.filter"
    ) as mock_filter:
        mock_filter.return_value = []

        widget = LLMHistoryWidget()
        widget.load_conversations()

        # Verify that filter was called correctly
        mock_filter.assert_called_once()
        # The call should be with a simple filter condition that doesn't cross session boundaries
        args, kwargs = mock_filter.call_args
        assert len(args) == 1  # Should have one filter condition
