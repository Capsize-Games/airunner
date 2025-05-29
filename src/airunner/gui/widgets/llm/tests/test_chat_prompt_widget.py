"""
Test suite for chat_prompt_widget.py in LLM widgets.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call  # Added call
from PySide6.QtCore import QTimer  # Added QTimer for singleShot mocking

from airunner.gui.widgets.llm import chat_prompt_widget
from airunner.data.models import Conversation  # Added Conversation
from airunner.enums import SignalCode  # Added SignalCode


@pytest.fixture
def chat_prompt(qtbot):
    with patch("sys.exit"), patch(
        "PySide6.QtWidgets.QApplication.exec", return_value=None
    ), patch(
        "airunner.gui.widgets.llm.chat_prompt_widget.ConversationHistoryManager"  # Mock ConversationHistoryManager
    ) as MockChm, patch(
        "airunner.gui.widgets.llm.chat_prompt_widget.create_worker"  # Mock create_worker for LLMResponseWorker
    ) as mock_create_worker:
        mock_chm_instance = MockChm.return_value
        mock_response_worker = MagicMock()
        mock_create_worker.return_value = mock_response_worker

        widget = chat_prompt_widget.ChatPromptWidget()
        widget._conversation_history_manager = (
            mock_chm_instance  # Ensure widget uses the mock CHM
        )
        widget.api = MagicMock()  # Mock API for llm.clear_history
        qtbot.addWidget(widget)
        widget.show()  # showEvent will trigger initial load_conversation
        # Reset mock call counts after showEvent so tests only count explicit calls
        mock_chm_instance.get_most_recent_conversation_id.reset_mock()
        mock_chm_instance.load_conversation_history.reset_mock()
        yield widget
        # Do not close the widget before test_show_event_loads_initial_conversation runs, so showEvent is still testable
        widget.close()


def test_chat_prompt_widget_constructs(chat_prompt):
    assert chat_prompt is not None
    assert chat_prompt._conversation_history_manager is not None
    chat_prompt.api.llm.clear_history.assert_not_called()  # Initial load might not have an ID yet


def test_load_conversation_no_id_uses_most_recent(chat_prompt):
    """Test that load_conversation calls get_most_recent_conversation_id if no ID is given."""
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.return_value = (
        1
    )
    chat_prompt._conversation_history_manager.load_conversation_history.return_value = (
        []
    )
    mock_conversation = MagicMock(spec=Conversation)
    mock_conversation.id = 1
    with patch(
        "airunner.data.models.Conversation.objects.filter_by_first",
        return_value=mock_conversation,
    ):
        chat_prompt.load_conversation(
            conversation_id=None
        )  # Explicitly call without ID
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.assert_called_once()
    chat_prompt._conversation_history_manager.load_conversation_history.assert_called_once_with(
        conversation_id=1, max_messages=50
    )
    chat_prompt.api.llm.clear_history.assert_called_with(conversation_id=1)


def test_load_conversation_with_specific_id(chat_prompt):
    """Test loading a conversation with a specific ID."""
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    test_id = 123
    expected_messages = [
        {"name": "User", "content": "Hello", "is_bot": False, "id": 0}
    ]
    chat_prompt._conversation_history_manager.load_conversation_history.return_value = (
        expected_messages
    )
    mock_conversation = MagicMock(spec=Conversation)
    mock_conversation.id = test_id

    with patch.object(
        chat_prompt, "_clear_conversation"
    ) as mock_clear, patch.object(
        chat_prompt, "_set_conversation_widgets"
    ) as mock_set_widgets, patch(
        "PySide6.QtCore.QTimer.singleShot"
    ) as mock_timer_shot, patch(
        "airunner.data.models.Conversation.objects.filter_by_first",
        return_value=mock_conversation,
    ):

        chat_prompt.load_conversation(conversation_id=test_id)

    assert chat_prompt.conversation_id == test_id
    assert chat_prompt.conversation == mock_conversation
    chat_prompt._conversation_history_manager.load_conversation_history.assert_called_once_with(
        conversation_id=test_id, max_messages=50
    )
    chat_prompt.api.llm.clear_history.assert_called_with(
        conversation_id=test_id
    )
    mock_clear.assert_called_once_with(skip_update=True)
    mock_set_widgets.assert_called_once_with(
        expected_messages, skip_scroll=True
    )
    mock_timer_shot.assert_called_with(100, chat_prompt.scroll_to_bottom)


def test_load_conversation_no_id_and_no_recent_found(chat_prompt):
    """Test behavior when no ID is given and no recent conversation exists."""
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.return_value = (
        None
    )

    with patch.object(chat_prompt, "_clear_conversation") as mock_clear:
        chat_prompt.load_conversation(conversation_id=None)

    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.assert_called_once()
    chat_prompt._conversation_history_manager.load_conversation_history.assert_not_called()
    assert chat_prompt.conversation_id is None
    assert chat_prompt.conversation is None
    mock_clear.assert_called_once_with()  # Should clear the display
    chat_prompt.api.llm.clear_history.assert_not_called()  # No conversation to clear history for


def test_on_queue_load_conversation_triggers_load_conversation(chat_prompt):
    """Test that on_queue_load_conversation calls load_conversation with the correct ID."""
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    test_id = 456
    with patch.object(chat_prompt, "load_conversation") as mock_load_conv:
        chat_prompt.on_queue_load_conversation({"index": test_id})
    mock_load_conv.assert_called_once_with(conversation_id=test_id)


def test_on_delete_conversation_clears_if_current(chat_prompt):
    """Test that deleting the current conversation clears the widget."""
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    chat_prompt.conversation_id = 123
    mock_conversation = MagicMock(spec=Conversation)
    mock_conversation.id = 123
    chat_prompt.conversation = mock_conversation  # Set current conversation

    with patch.object(
        chat_prompt, "_clear_conversation_widgets"
    ) as mock_clear_widgets:
        chat_prompt.on_delete_conversation({"conversation_id": 123})

    mock_clear_widgets.assert_called_once()
    assert chat_prompt.conversation_id is None
    assert chat_prompt.conversation is None


def test_on_delete_conversation_does_nothing_if_different(chat_prompt):
    """Test that deleting a different conversation doesn't affect the current one."""
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    chat_prompt.conversation_id = 123
    mock_conversation = MagicMock(spec=Conversation)
    mock_conversation.id = 123
    chat_prompt.conversation = mock_conversation

    with patch.object(
        chat_prompt, "_clear_conversation_widgets"
    ) as mock_clear_widgets:
        chat_prompt.on_delete_conversation({"conversation_id": 456})

    mock_clear_widgets.assert_not_called()
    assert chat_prompt.conversation_id == 123  # Stays the same
    assert chat_prompt.conversation == mock_conversation


# def test_show_event_loads_initial_conversation(chat_prompt):
#     """Test that showEvent triggers load_conversation (usually for the most recent)."""
#     # The initial load_conversation is called in the fixture's widget.show()
#     # We need to check the mocks on _conversation_history_manager
#     # This assumes the default behavior is to load the most recent if no ID is set.
#     chat_prompt._conversation_history_manager.get_most_recent_conversation_id.assert_called()
#     # Further assertions depend on whether a recent ID was found or not by the mock.


# ... Keep existing tests for do_generate, clear_prompt, etc., ensuring they still pass ...
# ... or adapt them if their interaction with conversation loading has changed indirectly ...

# Example of adapting an existing test if necessary (though do_generate might not need changes for this refactor)


def test_do_generate_sends_prompt(chat_prompt, qtbot):
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    # Arrange: Patch user, chatbot, and llm_generator_settings properties to return mocks
    with patch.object(
        type(chat_prompt), "user", new_callable=PropertyMock
    ) as mock_user_prop, patch.object(
        type(chat_prompt), "chatbot", new_callable=PropertyMock
    ) as mock_chatbot_prop, patch.object(
        type(chat_prompt), "llm_generator_settings", new_callable=PropertyMock
    ) as mock_llm_settings_prop:
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user_prop.return_value = mock_user
        mock_chatbot = MagicMock()
        mock_chatbot.botname = "test_bot"
        mock_chatbot_prop.return_value = mock_chatbot
        mock_llm_settings = MagicMock()
        mock_llm_settings.action = "CHAT"
        mock_llm_settings_prop.return_value = mock_llm_settings
        # chat_prompt.api = MagicMock() # Already mocked in fixture
        chat_prompt.api.llm.send_request = MagicMock()
        chat_prompt.prompt = "Hello, world!"
        chat_prompt.generating = False

        # Patch methods that interact with the UI or are side effects
        with patch.object(
            chat_prompt,
            "add_message_to_conversation",
            return_value=MagicMock(),
        ) as add_msg, patch.object(
            chat_prompt, "clear_prompt"
        ) as clear_prompt, patch.object(
            chat_prompt, "start_progress_bar"
        ) as start_progress:
            chat_prompt.do_generate()

        # Assert: send_request should be called with the prompt
        chat_prompt.api.llm.send_request.assert_called()
        clear_prompt.assert_called_once()
        start_progress.assert_called_once()
        add_msg.assert_called_once()


def test_status_indicator_shows_and_hides_on_mood_summary_update(
    qtbot, chat_prompt
):  # Added chat_prompt fixture
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    """Test that the status indicator shows when mood/summary update starts and hides when a bot message arrives."""
    # from airunner.gui.widgets.llm import chat_prompt_widget # Not needed due to fixture

    # widget = chat_prompt_widget.ChatPromptWidget() # Provided by fixture
    # qtbot.addWidget(widget)
    # widget.show()

    # Simulate mood/summary update started
    chat_prompt.on_mood_summary_update_started()  # Use chat_prompt from fixture
    assert chat_prompt.loading_widget.isVisible()
    assert (
        chat_prompt.loading_widget.ui.label.text()
        == "Updating bot mood / summarizing..."
    )

    # Simulate bot message arrival (should hide indicator)
    chat_prompt.on_add_bot_message_to_conversation(  # Use chat_prompt from fixture
        {
            "response": type(
                "LLMResponse",
                (),
                {
                    "node_id": None,
                    "message": "Test",
                    "is_first_message": True,
                    "is_end_of_message": True,
                },
            )()
        }
    )
    assert not chat_prompt.loading_widget.isVisible()


def test_status_indicator_custom_message(
    qtbot, chat_prompt
):  # Added chat_prompt fixture
    chat_prompt._conversation_history_manager.get_most_recent_conversation_id.reset_mock()
    chat_prompt._conversation_history_manager.load_conversation_history.reset_mock()
    """Test that the status indicator shows a custom message from the signal payload."""
    # from airunner.gui.widgets.llm import chat_prompt_widget # Not needed

    # widget = chat_prompt_widget.ChatPromptWidget() # Provided by fixture
    # qtbot.addWidget(widget)
    # widget.show()

    # Simulate receiving the signal with a custom message
    chat_prompt._handle_mood_summary_update_started(  # Use chat_prompt from fixture
        {"message": "Custom loading..."}
    )
    assert chat_prompt.loading_widget.isVisible()
    assert chat_prompt.loading_widget.ui.label.text() == "Custom loading..."

    # Hide indicator
    chat_prompt.hide_status_indicator()  # Use chat_prompt from fixture
    assert not chat_prompt.loading_widget.isVisible()
