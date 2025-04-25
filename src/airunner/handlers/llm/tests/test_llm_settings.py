import unittest
from unittest.mock import patch

from airunner.handlers.llm.llm_settings import LLMSettings


class TestLLMSettings(unittest.TestCase):
    """Test suite for the LLMSettings class functionality."""

    def test_default_initialization(self):
        """Test that LLMSettings initializes with default values from settings."""
        with patch(
            "airunner.handlers.llm.llm_settings.AIRUNNER_LLM_USE_OPENAI", False
        ):

            settings = LLMSettings()

            # Verify correct default values
            self.assertTrue(settings.use_local_llm)
            self.assertFalse(settings.use_openrouter)
            self.assertFalse(settings.use_openai)

    def test_use_api_property_openrouter(self):
        """Test that use_api property returns correct value when openrouter is enabled."""
        settings = LLMSettings()
        settings.use_openrouter = True
        settings.use_openai = False

        # Verify use_api is True when openrouter is enabled
        self.assertTrue(settings.use_api)

    def test_use_api_property_openai(self):
        """Test that use_api property returns correct value when openai is enabled."""
        settings = LLMSettings()
        settings.use_openrouter = False
        settings.use_openai = True

        # Verify use_api is True when openai is enabled
        self.assertTrue(settings.use_api)

    def test_use_api_property_both_false(self):
        """Test that use_api property returns False when both API settings are disabled."""
        settings = LLMSettings()
        settings.use_openrouter = False
        settings.use_openai = False

        # Verify use_api is False when both APIs are disabled
        self.assertFalse(settings.use_api)

    def test_use_api_property_both_true(self):
        """Test that use_api property returns True when both API settings are enabled."""
        settings = LLMSettings()
        settings.use_openrouter = True
        settings.use_openai = True

        # Verify use_api is True when both APIs are enabled
        self.assertTrue(settings.use_api)


if __name__ == "__main__":
    unittest.main()
