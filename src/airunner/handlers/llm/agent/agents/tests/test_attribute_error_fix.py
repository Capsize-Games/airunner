"""Test to verify the AttributeError fix in BaseAgent mood and user data analysis."""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.handlers.llm.agent.agents.base import BaseAgent


class TestBaseAgentAttributeErrorFix(unittest.TestCase):
    """Test that the ChatResponse attribute access fix works correctly."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a BaseAgent instance with minimal mocking
        with patch.object(BaseAgent, "__init__", return_value=None):
            self.agent = BaseAgent()

        # Mock the required attributes - use property mocking for logger
        self.logger_mock = MagicMock()
        self.logger_patcher = patch.object(
            BaseAgent, "logger", new_callable=lambda: self.logger_mock
        )
        self.logger_patcher.start()

        # Mock the analysis_tool property using PropertyMock
        self.analysis_tool_mock = MagicMock()
        self.analysis_tool_patcher = patch.object(
            BaseAgent, "analysis_tool", new_callable=PropertyMock
        )
        self.analysis_tool_property = self.analysis_tool_patcher.start()
        self.analysis_tool_property.return_value = self.analysis_tool_mock

        # Mock the mood_engine property using PropertyMock
        self.mood_engine_mock = MagicMock()
        self.mood_engine_patcher = patch.object(
            BaseAgent, "mood_engine", new_callable=PropertyMock
        )
        self.mood_engine_property = self.mood_engine_patcher.start()
        self.mood_engine_property.return_value = self.mood_engine_mock

        # Mock the update_user_data_engine property using PropertyMock
        self.user_data_engine_mock = MagicMock()
        self.user_data_engine_patcher = patch.object(
            BaseAgent, "update_user_data_engine", new_callable=PropertyMock
        )
        self.user_data_engine_property = self.user_data_engine_patcher.start()
        self.user_data_engine_property.return_value = (
            self.user_data_engine_mock
        )

        # Patch the mood_tool property to avoid calling real logic (which requires mediator)
        self.mood_tool_mock = MagicMock()
        self.mood_tool_patcher = patch.object(
            BaseAgent, "mood_tool", new_callable=PropertyMock
        )
        self.mood_tool_property = self.mood_tool_patcher.start()
        self.mood_tool_property.return_value = self.mood_tool_mock

        # Patch required internal attributes to avoid AttributeError
        self.agent._use_memory = True

        # Patch llm property (read-only) with PropertyMock
        self.llm_patcher = patch.object(
            BaseAgent, "llm", new_callable=PropertyMock
        )
        self.llm_property = self.llm_patcher.start()
        self.llm_property.return_value = None

        # Patch llm_request property (has setter, but patch for safety)
        self.llm_request_patcher = patch.object(
            BaseAgent, "llm_request", new_callable=PropertyMock
        )
        self.llm_request_property = self.llm_request_patcher.start()
        self.llm_request_property.return_value = None

        self.agent.update_chatbot_mood = MagicMock()

    def tearDown(self):
        """Clean up test fixtures."""
        self.logger_patcher.stop()
        self.analysis_tool_patcher.stop()
        self.mood_engine_patcher.stop()
        self.user_data_engine_patcher.stop()
        self.llm_patcher.stop()
        self.llm_request_patcher.stop()
        self.mood_tool_patcher.stop()

    def test_update_mood_with_correct_response_access(self):
        """Test that _update_mood correctly accesses response.message instead of response.message.content."""
        # Mock the conversation
        mock_conversation = MagicMock()
        mock_conversation.value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_conversation.id = 1
        mock_conversation.formatted_messages = "formatted conversation"

        # Mock the mood engine response - this is what was causing the AttributeError
        mock_response = MagicMock()
        mock_response.message = (
            '{"mood": "happy", "emoji": "😊"}'  # The message IS the content
        )

        # Set the mood_engine mock's chat return value
        self.mood_engine_mock.chat.return_value = mock_response

        # Assign the mock conversation to the agent
        self.agent.conversation = mock_conversation

        # Mock the chatbot update
        self.agent.update_chatbot_mood = MagicMock()

        # This should NOT raise an AttributeError anymore
        try:
            self.agent._update_mood()
            # If we get here, the fix worked
            self.assertTrue(True)
        except AttributeError as e:
            if "'name'" in str(e):
                self.fail(f"AttributeError still occurs: {e}")
            else:
                # Some other AttributeError, re-raise
                raise

        # Verify the mood engine was called
        self.mood_engine_mock.chat.assert_called_once_with(
            "formatted conversation"
        )

        # Verify chatbot mood was updated
        self.agent.update_chatbot_mood.assert_not_called()  # update_chatbot_mood is not called in _update_mood, mood_tool is used

    def test_update_user_data_with_correct_response_access(self):
        """Test that _update_user_data correctly accesses response.message instead of response.message.content."""
        # Mock the conversation
        mock_conversation = MagicMock()
        mock_conversation.value = [
            {"role": "user", "content": "I love programming"},
            {"role": "assistant", "content": "That's great!"},
        ]
        mock_conversation.id = 1
        mock_conversation.formatted_messages = "formatted conversation"

        # Mock the user data engine response - this is what was causing the AttributeError
        mock_response = MagicMock()
        mock_response.message = "User enjoys programming and technology"  # The message IS the content

        # Set the update_user_data_engine mock's chat return value
        self.user_data_engine_mock.chat.return_value = mock_response

        # Assign the mock conversation to the agent
        self.agent.conversation = mock_conversation

        # This should NOT raise an AttributeError anymore
        try:
            self.agent._update_user_data()
            # If we get here, the fix worked
            self.assertTrue(True)
        except AttributeError as e:
            if "'name'" in str(e):
                self.fail(f"AttributeError still occurs: {e}")
            else:
                # Some other AttributeError, re-raise
                raise

        # Verify the user data engine was called
        self.user_data_engine_mock.chat.assert_called_once_with(
            "formatted conversation"
        )

        # Verify that user_data was updated correctly
        self.assertEqual(
            mock_conversation.user_data,
            ["User enjoys programming and technology"],
        )
        # No call to analysis_tool should be made
        self.agent.analysis_tool.assert_not_called()


if __name__ == "__main__":
    unittest.main()
