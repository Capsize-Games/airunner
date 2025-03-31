import unittest
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.enums import LLMActionType


class TestLLMResponse(unittest.TestCase):
    """Test suite for the LLMResponse class functionality."""

    def test_default_initialization(self):
        """Test that LLMResponse initializes with default values."""
        response = LLMResponse()
        
        # Verify correct default values
        self.assertEqual(response.message, "")
        self.assertFalse(response.is_first_message)
        self.assertFalse(response.is_end_of_message)
        self.assertIsNone(response.name)
        self.assertEqual(response.action, LLMActionType.CHAT)

    def test_custom_initialization(self):
        """Test that LLMResponse initializes with custom values."""
        response = LLMResponse(
            message="Hello, world!",
            is_first_message=True,
            is_end_of_message=True,
            name="Assistant",
            action=LLMActionType.UPDATE_MOOD
        )
        
        # Verify custom values were set correctly
        self.assertEqual(response.message, "Hello, world!")
        self.assertTrue(response.is_first_message)
        self.assertTrue(response.is_end_of_message)
        self.assertEqual(response.name, "Assistant")
        self.assertEqual(response.action, LLMActionType.UPDATE_MOOD)

    def test_end_message_only(self):
        """Test creating an end-of-message signal."""
        response = LLMResponse(is_end_of_message=True)
        
        # Verify end message flag is set but content is empty
        self.assertTrue(response.is_end_of_message)
        self.assertEqual(response.message, "")
        self.assertFalse(response.is_first_message)


if __name__ == '__main__':
    unittest.main()