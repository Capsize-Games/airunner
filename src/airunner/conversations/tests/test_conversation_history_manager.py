"""Tests for the ConversationHistoryManager."""

import pytest
from unittest.mock import patch, MagicMock

from airunner.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.data.models import (
    Conversation,
)  # Assuming Conversation is a dataclass or similar

# Mock data for Conversation objects
MOCK_USER_NAME = "Test User"
MOCK_CHATBOT_NAME = "Test Bot"


def create_mock_conversation_data(
    conv_id: int,
    messages: list,
    user_name: str = MOCK_USER_NAME,
    chatbot_name: str = MOCK_CHATBOT_NAME,
) -> MagicMock:
    mock_conv = MagicMock(spec=Conversation)
    mock_conv.id = conv_id
    mock_conv.value = messages
    mock_conv.user_name = user_name
    mock_conv.chatbot_name = chatbot_name
    return mock_conv


@pytest.fixture
def mock_conversation_model():
    with patch(
        "airunner.conversations.conversation_history_manager.Conversation"
    ) as mock_conv_cls:
        yield mock_conv_cls


@pytest.fixture
def manager() -> ConversationHistoryManager:
    """Provides an instance of ConversationHistoryManager with a mocked logger."""
    mgr = ConversationHistoryManager()
    mgr.logger = MagicMock()
    return mgr


def test_conversation_history_manager_initialization(
    manager: ConversationHistoryManager,
):
    """Tests that the ConversationHistoryManager initializes correctly."""
    assert manager is not None
    assert manager.logger is not None


# Tests for get_most_recent_conversation_id
def test_get_most_recent_conversation_id_exists(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests get_most_recent_conversation_id when a conversation exists."""
    mock_conv = create_mock_conversation_data(123, [])
    mock_conversation_model.most_recent.return_value = mock_conv

    conv_id = manager.get_most_recent_conversation_id()
    assert conv_id == 123
    mock_conversation_model.most_recent.assert_called_once()


def test_get_most_recent_conversation_id_none_exists(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests get_most_recent_conversation_id when no conversations exist."""
    mock_conversation_model.most_recent.return_value = None

    conv_id = manager.get_most_recent_conversation_id()
    assert conv_id is None
    mock_conversation_model.most_recent.assert_called_once()


def test_get_most_recent_conversation_id_exception(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests get_most_recent_conversation_id when an exception occurs."""
    mock_conversation_model.most_recent.side_effect = Exception("DB error")

    conv_id = manager.get_most_recent_conversation_id()
    assert conv_id is None
    mock_conversation_model.most_recent.assert_called_once()
    manager.logger.error.assert_called_once()


# Tests for load_conversation_history
def test_load_conversation_history_with_id(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests loading history with a specific conversation ID."""
    mock_messages = [
        {"role": "user", "user_name": "Alice", "blocks": [{"text": "Hello"}]},
        {"role": "assistant", "bot_name": "Bob", "blocks": [{"text": "Hi"}]},
    ]
    mock_conv = create_mock_conversation_data(
        conv_id=1, messages=mock_messages
    )
    mock_conversation_model.objects.filter_by_first.return_value = mock_conv

    history = manager.load_conversation_history(conversation_id=1)

    assert len(history) == 2
    assert history[0]["name"] == "Alice"
    assert history[0]["content"] == "Hello"
    assert not history[0]["is_bot"]
    assert history[0]["id"] == 0
    assert history[1]["name"] == "Bob"
    assert history[1]["content"] == "Hi"
    assert history[1]["is_bot"]
    assert history[1]["id"] == 1
    mock_conversation_model.objects.filter_by_first.assert_called_once_with(
        id=1
    )


def test_load_conversation_history_most_recent(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests loading history for the most recent conversation (ID is None)."""
    mock_messages = [{"role": "user", "blocks": [{"text": "Recent"}]}]
    mock_conv = create_mock_conversation_data(
        conv_id=2, messages=mock_messages
    )
    mock_conversation_model.most_recent.return_value = mock_conv

    history = manager.load_conversation_history()

    assert len(history) == 1
    assert history[0]["content"] == "Recent"
    mock_conversation_model.most_recent.assert_called_once()


def test_load_conversation_history_not_found(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests loading history when the conversation is not found."""
    mock_conversation_model.objects.filter_by_first.return_value = None
    history = manager.load_conversation_history(conversation_id=999)
    assert history == []
    manager.logger.warning.assert_called_once()


def test_load_conversation_history_empty_messages(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests loading history when the conversation has no messages."""
    mock_conv = create_mock_conversation_data(conv_id=3, messages=[])
    mock_conversation_model.objects.filter_by_first.return_value = mock_conv
    history = manager.load_conversation_history(conversation_id=3)
    assert history == []
    manager.logger.info.assert_any_call("Conversation 3 is empty.")


def test_load_conversation_history_invalid_message_data_not_list(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests loading history when conversation.value is not a list."""
    mock_conv = create_mock_conversation_data(conv_id=3, messages="not a list")
    mock_conversation_model.objects.filter_by_first.return_value = mock_conv
    history = manager.load_conversation_history(conversation_id=3)
    assert history == []
    manager.logger.warning.assert_called_once_with(
        "Conversation 3 has invalid message data (not a list): <class 'str'>"
    )


def test_load_conversation_history_invalid_message_object_in_list(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests loading history when a message object in the list is not a dict."""
    mock_messages = [
        {"role": "user", "user_name": "Alice", "blocks": [{"text": "Hello"}]},
        "not a dict",
        {"role": "assistant", "bot_name": "Bob", "blocks": [{"text": "Hi"}]},
    ]
    mock_conv = create_mock_conversation_data(
        conv_id=4, messages=mock_messages
    )
    mock_conversation_model.objects.filter_by_first.return_value = mock_conv

    history = manager.load_conversation_history(conversation_id=4)
    assert len(history) == 2
    assert history[0]["content"] == "Hello"
    assert history[1]["content"] == "Hi"
    manager.logger.warning.assert_called_once_with(
        "Skipping invalid message object (not a dict) in conversation 4: not a dict"
    )


def test_load_conversation_history_max_messages(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests the max_messages limit."""
    mock_messages = [
        {"role": "user", "blocks": [{"text": f"Msg {i}"}]} for i in range(10)
    ]  # 10 messages
    mock_conv = create_mock_conversation_data(
        conv_id=4, messages=mock_messages
    )
    mock_conversation_model.objects.filter_by_first.return_value = mock_conv

    history = manager.load_conversation_history(
        conversation_id=4, max_messages=5
    )
    assert len(history) == 5
    assert history[0]["content"] == "Msg 5"  # Should get messages 5-9
    assert history[4]["content"] == "Msg 9"


def test_load_conversation_history_message_formatting(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests the detailed formatting of messages."""
    mock_messages = [
        {
            "role": "user",
            "user_name": "User1",
            "blocks": [{"text": "Question?"}],
        },
        {
            "role": "assistant",
            "bot_name": "Bot1",
            "blocks": [{"text": "Answer."}],
        },
        {  # Message with missing user_name/bot_name, should use conv default
            "role": "user",
            "blocks": [{"text": "Follow up"}],
        },
        {  # Message with missing blocks
            "role": "assistant",
            "bot_name": "Bot1",
        },
        {  # Message with empty blocks list
            "role": "user",
            "user_name": "User1",
            "blocks": [],
        },
        {  # Message with block not being a dict
            "role": "assistant",
            "bot_name": "Bot1",
            "blocks": ["not a dict block"],
        },
        {  # Message with block missing 'text'
            "role": "user",
            "user_name": "User1",
            "blocks": [{"type": "image"}],
        },
    ]
    mock_conv = create_mock_conversation_data(
        conv_id=5,
        messages=mock_messages,
        user_name="DefaultUser",
        chatbot_name="DefaultBot",
    )
    mock_conversation_model.objects.filter_by_first.return_value = mock_conv

    history = manager.load_conversation_history(conversation_id=5)

    assert len(history) == 7

    assert history[0]["name"] == "User1"
    assert history[0]["content"] == "Question?"
    assert not history[0]["is_bot"]
    assert history[0]["id"] == 0

    assert history[1]["name"] == "Bot1"
    assert history[1]["content"] == "Answer."
    assert history[1]["is_bot"]
    assert history[1]["id"] == 1

    assert history[2]["name"] == "DefaultUser"  # Used conversation default
    assert history[2]["content"] == "Follow up"
    assert not history[2]["is_bot"]
    assert history[2]["id"] == 2

    assert history[3]["name"] == "Bot1"
    assert history[3]["content"] == ""  # Missing blocks
    assert history[3]["is_bot"]
    assert history[3]["id"] == 3

    assert history[4]["name"] == "User1"
    assert history[4]["content"] == ""  # Empty blocks list
    assert not history[4]["is_bot"]
    assert history[4]["id"] == 4

    assert history[5]["name"] == "Bot1"
    assert history[5]["content"] == ""  # Block not a dict
    assert history[5]["is_bot"]
    assert history[5]["id"] == 5

    assert history[6]["name"] == "User1"
    assert history[6]["content"] == ""  # Block missing 'text'
    assert not history[6]["is_bot"]
    assert history[6]["id"] == 6


def test_load_conversation_history_exception_during_load(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests behavior when an exception occurs during history loading."""
    mock_conversation_model.objects.filter_by_first.side_effect = Exception(
        "DB Read Error"
    )
    history = manager.load_conversation_history(conversation_id=1)
    assert history == []
    manager.logger.error.assert_called_once()


def test_load_conversation_history_uses_conversation_names_if_message_names_missing(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests that conversation level user_name and chatbot_name are used as fallbacks."""
    mock_messages = [
        {
            "role": "user",
            "blocks": [{"text": "Hello from user"}],
        },  # No user_name
        {
            "role": "assistant",
            "blocks": [{"text": "Hi from bot"}],
        },  # No bot_name
    ]
    mock_conv = create_mock_conversation_data(
        conv_id=1,
        messages=mock_messages,
        user_name="ConvUser",
        chatbot_name="ConvBot",
    )
    mock_conversation_model.objects.filter_by_first.return_value = mock_conv

    history = manager.load_conversation_history(conversation_id=1)

    assert len(history) == 2
    assert history[0]["name"] == "ConvUser"
    assert history[0]["content"] == "Hello from user"
    assert not history[0]["is_bot"]

    assert history[1]["name"] == "ConvBot"
    assert history[1]["content"] == "Hi from bot"
    assert history[1]["is_bot"]


def test_load_conversation_history_uses_default_names_if_all_names_missing(
    manager: ConversationHistoryManager, mock_conversation_model: MagicMock
):
    """Tests that 'User' and 'Bot' are used if no names are available anywhere."""
    mock_messages = [
        {"role": "user", "blocks": [{"text": "User message"}]},
        {"role": "assistant", "blocks": [{"text": "Bot message"}]},
    ]
    # Create a mock conversation where user_name and chatbot_name are None or empty
    mock_conv = MagicMock(spec=Conversation)
    mock_conv.id = 1
    mock_conv.value = mock_messages
    mock_conv.user_name = None
    mock_conv.chatbot_name = ""
    mock_conversation_model.objects.filter_by_first.return_value = mock_conv

    history = manager.load_conversation_history(conversation_id=1)

    assert len(history) == 2
    assert history[0]["name"] == "User"
    assert history[1]["name"] == "Bot"
