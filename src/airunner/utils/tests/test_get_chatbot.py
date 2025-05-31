"""
Test suite for get_chatbot() in airunner.utils.llm.get_chatbot.

Covers correct eager loading and error-free operation.
"""

import pytest
from unittest.mock import patch, MagicMock
from airunner.utils.llm import get_chatbot
from airunner.data.models.chatbot import Chatbot


def test_get_chatbot_returns_chatbot(monkeypatch):
    """Test that get_chatbot returns a Chatbot instance and does not log errors."""
    # Patch Chatbot.objects methods to simulate DB
    mock_chatbot = MagicMock(spec=Chatbot)
    mock_chatbot.name = "TestBot"
    mock_chatbot.target_files = []
    mock_chatbot.target_directories = []

    class MockObjects:
        @staticmethod
        def filter_by_first(*args, **kwargs):
            return mock_chatbot

        @staticmethod
        def first(*args, **kwargs):
            return mock_chatbot

        @staticmethod
        def create(*args, **kwargs):
            return mock_chatbot

    monkeypatch.setattr(Chatbot, "objects", MockObjects)
    monkeypatch.setattr(get_chatbot, "Chatbot", Chatbot)

    with patch("airunner.utils.llm.get_chatbot.get_logger") as mock_logger:
        chatbot = get_chatbot.get_chatbot()
        assert chatbot is mock_chatbot
        # Should not log errors
        mock_logger.return_value.error.assert_not_called()
        # Eager loaded attributes should be present
        assert hasattr(chatbot, "target_files")
        assert hasattr(chatbot, "target_directories")
