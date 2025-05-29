"""
Test suite for LLMChatPromptWorker.
"""

import pytest
from unittest.mock import MagicMock, patch

from airunner.workers.llm_chat_prompt_worker import LLMChatPromptWorker
from airunner.enums import SignalCode


@pytest.fixture
def worker():
    """Provides an LLMChatPromptWorker instance with a mocked ConversationHistoryManager."""
    with patch(
        "airunner.workers.llm_chat_prompt_worker.ConversationHistoryManager"
    ) as MockChm:
        mock_chm_instance = MockChm.return_value
        worker_instance = LLMChatPromptWorker()
        worker_instance._conversation_history_manager = (
            mock_chm_instance  # Ensure worker uses the mock
        )
        worker_instance.emit_signal = MagicMock()  # Mock the signal emission
        yield worker_instance


def test_handle_message_load_conversation_with_id(worker: LLMChatPromptWorker):
    """Test loading a conversation with a specific ID."""
    conversation_id = 123
    message = {"action": "load_conversation", "index": conversation_id}

    worker.handle_message(message)

    worker.emit_signal.assert_called_once_with(
        SignalCode.QUEUE_LOAD_CONVERSATION, {"index": conversation_id}
    )
    worker._conversation_history_manager.get_most_recent_conversation_id.assert_not_called()


def test_handle_message_load_conversation_no_id_found(
    worker: LLMChatPromptWorker,
):
    """Test loading a conversation when no ID is provided and a recent one is found."""
    recent_conversation_id = 456
    worker._conversation_history_manager.get_most_recent_conversation_id.return_value = (
        recent_conversation_id
    )
    message = {"action": "load_conversation", "index": None}

    worker.handle_message(message)

    worker.emit_signal.assert_called_once_with(
        SignalCode.QUEUE_LOAD_CONVERSATION, {"index": recent_conversation_id}
    )
    worker._conversation_history_manager.get_most_recent_conversation_id.assert_called_once()


def test_handle_message_load_conversation_no_id_none_found(
    worker: LLMChatPromptWorker,
):
    """Test loading a conversation when no ID is provided and no recent one is found."""
    worker._conversation_history_manager.get_most_recent_conversation_id.return_value = (
        None
    )
    message = {"action": "load_conversation", "index": None}

    worker.handle_message(message)

    worker.emit_signal.assert_called_once_with(
        SignalCode.QUEUE_LOAD_CONVERSATION, {"index": None}
    )
    worker._conversation_history_manager.get_most_recent_conversation_id.assert_called_once()


def test_handle_message_unknown_action(worker: LLMChatPromptWorker):
    """Test that unknown actions do not cause errors or emit signals."""
    message = {"action": "unknown_action"}
    worker.handle_message(message)
    worker.emit_signal.assert_not_called()


def test_handle_message_no_action(worker: LLMChatPromptWorker):
    """Test that messages without an action do not cause errors or emit signals."""
    message = {"index": 123}  # No 'action' key
    worker.handle_message(message)
    worker.emit_signal.assert_not_called()
