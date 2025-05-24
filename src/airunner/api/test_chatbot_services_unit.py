"""
Unit tests for ChatbotAPIService.
Tests signal emission for bot mood updates.
"""

import pytest
from unittest.mock import MagicMock
from airunner.api.chatbot_services import ChatbotAPIService
from airunner.enums import SignalCode


class TestChatbotAPIService:
    """Test cases for ChatbotAPIService"""

    @pytest.fixture
    def mock_emit_signal(self):
        """Mock the emit_signal property to capture signal emissions"""
        mock_emit_signal = MagicMock()
        return mock_emit_signal

    @pytest.fixture
    def chatbot_service(self, mock_emit_signal):
        """Create ChatbotAPIService instance with mocked emit_signal"""
        service = ChatbotAPIService(emit_signal=mock_emit_signal)
        yield service

    def test_update_mood_happy_path(self, chatbot_service, mock_emit_signal):
        """Test update_mood with valid mood string"""
        mood = "happy"

        chatbot_service.update_mood(mood)

        mock_emit_signal.assert_called_once_with(
            SignalCode.BOT_MOOD_UPDATED, {"mood": mood}
        )

    def test_update_mood_different_moods(
        self, chatbot_service, mock_emit_signal
    ):
        """Test update_mood with various mood values"""
        test_moods = ["sad", "excited", "confused", "angry", "neutral"]

        for mood in test_moods:
            mock_emit_signal.reset_mock()
            chatbot_service.update_mood(mood)
            mock_emit_signal.assert_called_once_with(
                SignalCode.BOT_MOOD_UPDATED, {"mood": mood}
            )

    def test_update_mood_none_value(self, chatbot_service, mock_emit_signal):
        """Test update_mood with None value"""
        chatbot_service.update_mood(None)

        mock_emit_signal.assert_called_once_with(
            SignalCode.BOT_MOOD_UPDATED, {"mood": None}
        )

    def test_update_mood_empty_string(self, chatbot_service, mock_emit_signal):
        """Test update_mood with empty string"""
        chatbot_service.update_mood("")

        mock_emit_signal.assert_called_once_with(
            SignalCode.BOT_MOOD_UPDATED, {"mood": ""}
        )

    def test_update_mood_numeric_value(
        self, chatbot_service, mock_emit_signal
    ):
        """Test update_mood with numeric value"""
        chatbot_service.update_mood(42)

        mock_emit_signal.assert_called_once_with(
            SignalCode.BOT_MOOD_UPDATED, {"mood": 42}
        )

    def test_update_mood_complex_object(
        self, chatbot_service, mock_emit_signal
    ):
        """Test update_mood with complex object"""
        mood_data = {"emotion": "happy", "intensity": 0.8}

        chatbot_service.update_mood(mood_data)

        mock_emit_signal.assert_called_once_with(
            SignalCode.BOT_MOOD_UPDATED, {"mood": mood_data}
        )
