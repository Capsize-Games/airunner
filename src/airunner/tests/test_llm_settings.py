import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.handlers.llm.agent.agents.base import BaseAgent
from airunner.data.models import Conversation

class TestBaseAgentUpdateUserData(unittest.TestCase):

    @patch('airunner.handlers.llm.agent.agents.base.BaseAgent.update_user_data_tool', new_callable=PropertyMock)
    @patch('airunner.handlers.llm.agent.agents.base.BaseAgent.chat_engine', new_callable=PropertyMock)
    @patch('airunner.handlers.llm.agent.agents.base.BaseAgent.username', new_callable=PropertyMock)
    @patch('airunner.handlers.llm.agent.agents.base.Conversation.objects.update')
    def test_update_user_data(self, mock_update, mock_username, mock_chat_engine, mock_update_user_data_tool):
        # Mock the response from the update_user_data_tool
        mock_update_user_data_tool.return_value.call.return_value.content = "User likes hiking.\nUser dislikes loud noises."
        # Mock the username property
        mock_username.return_value = "TestUser"
        # Mock the chat_engine property
        mock_chat_engine.return_value = MagicMock()
        # Create a mock conversation
        mock_conversation = MagicMock()
        mock_conversation.user_data = []
        
        # Create an instance of BaseAgent
        agent = BaseAgent()
        agent.conversation = mock_conversation
        # Call the method
        agent._update_user_data()
        # Assert the update method was called with concise summaries
        mock_update.assert_called_once_with(
            mock_conversation.id,
            user_data=["User likes hiking.", "User dislikes loud noises."]
        )

    @patch('airunner.handlers.llm.agent.agents.base.BaseAgent.update_user_data_tool', new_callable=PropertyMock)
    @patch('airunner.handlers.llm.agent.agents.base.BaseAgent.chat_engine', new_callable=PropertyMock)
    @patch('airunner.handlers.llm.agent.agents.base.BaseAgent.username', new_callable=PropertyMock)
    @patch('airunner.handlers.llm.agent.agents.base.Conversation.objects.update')
    def test_update_user_data_no_meaningful_info(self, mock_update, mock_username, mock_chat_engine, mock_update_user_data_tool):
        # Mock the response from the update_user_data_tool with no meaningful content
        mock_update_user_data_tool.return_value.call.return_value.content = ""
        # Mock the username property
        mock_username.return_value = "TestUser"
        # Mock the chat_engine property
        mock_chat_engine.return_value = MagicMock()
        # Create a mock conversation
        mock_conversation = MagicMock()
        mock_conversation.user_data = []
        
        # Create an instance of BaseAgent
        agent = BaseAgent()
        agent.conversation = mock_conversation
        # Call the method
        agent._update_user_data()
        # Assert the update method was not called
        mock_update.assert_not_called()

if __name__ == "__main__":
    unittest.main()