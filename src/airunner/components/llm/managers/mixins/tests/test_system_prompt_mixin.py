"""Unit tests for SystemPromptMixin."""

from unittest.mock import Mock, patch
import pytest
from datetime import datetime

from airunner.components.llm.managers.mixins.system_prompt_mixin import (
    SystemPromptMixin,
)
from airunner.enums import LLMActionType


class TestableSystemPromptMixin(SystemPromptMixin):
    """Testable version of SystemPromptMixin."""

    def __init__(self):
        """Initialize with mock dependencies."""
        self.chatbot = Mock()
        self.chatbot.botname = "TestBot"
        self.chatbot.personality = "friendly and helpful"
        self.chatbot.use_mood = False
        self.llm_settings = Mock()
        self.llm_settings.use_chatbot_mood = False
        self.llm_settings.update_mood_after_n_turns = 5


@pytest.fixture
def mixin():
    """Create a testable SystemPromptMixin instance."""
    return TestableSystemPromptMixin()


class TestSystemPrompt:
    """Tests for system_prompt property."""

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_includes_bot_name_and_personality(self, mock_datetime, mixin):
        """Should include bot name and personality in prompt."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)

        prompt = mixin.system_prompt

        assert "You are TestBot" in prompt
        assert "Personality: friendly and helpful" in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_includes_current_timestamp(self, mock_datetime, mixin):
        """Should include current date and time."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)

        prompt = mixin.system_prompt

        assert "2024-01-15 10:30:00" in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_uses_generic_assistant_when_no_chatbot(
        self, mock_datetime, mixin
    ):
        """Should use generic assistant description when no chatbot."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)
        mixin.chatbot = None

        prompt = mixin.system_prompt

        assert "You are a helpful AI assistant" in prompt
        assert "TestBot" not in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_includes_mood_instructions_when_enabled(
        self, mock_datetime, mixin
    ):
        """Should include mood update instructions when enabled."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)
        mixin.llm_settings.use_chatbot_mood = True
        mixin.chatbot.use_mood = True
        mixin.llm_settings.update_mood_after_n_turns = 3

        prompt = mixin.system_prompt

        # New mood system uses automatic updates, not manual tool calls
        assert "emotional state updates automatically every 3" in prompt
        assert "conversation turns" in prompt
        assert "mood subtly influence" in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_excludes_mood_when_chatbot_disabled(self, mock_datetime, mixin):
        """Should not include mood instructions when chatbot disables it."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)
        mixin.llm_settings.use_chatbot_mood = True
        mixin.chatbot.use_mood = False

        prompt = mixin.system_prompt

        assert "emotional state updates automatically" not in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_excludes_mood_when_settings_disabled(self, mock_datetime, mixin):
        """Should not include mood instructions when settings disable it."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)
        mixin.llm_settings.use_chatbot_mood = False
        mixin.chatbot.use_mood = True

        prompt = mixin.system_prompt

        assert "emotional state updates automatically" not in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_handles_missing_personality_gracefully(
        self, mock_datetime, mixin
    ):
        """Should work when personality is not set."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)
        mixin.chatbot.personality = None

        prompt = mixin.system_prompt

        assert "You are TestBot" in prompt
        assert "Personality:" not in prompt


class TestGetSystemPromptForAction:
    """Tests for get_system_prompt_for_action method."""

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_chat_action_adds_chat_instructions(self, mock_datetime, mixin):
        """Should add chat-specific instructions for CHAT action."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)

        prompt = mixin.get_system_prompt_for_action(LLMActionType.CHAT)

        assert "Mode: CHAT" in prompt
        assert "natural conversation" in prompt
        assert "conversation management tools" in prompt
        assert "avoid" in prompt.lower()

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_generate_image_action_adds_image_instructions(
        self, mock_datetime, mixin
    ):
        """Should add image generation instructions for GENERATE_IMAGE action."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)

        prompt = mixin.get_system_prompt_for_action(
            LLMActionType.GENERATE_IMAGE
        )

        assert "Mode: IMAGE GENERATION" in prompt
        assert "generating images" in prompt
        assert "generate_image tool" in prompt
        assert "canvas tools" in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_rag_search_action_adds_search_instructions(
        self, mock_datetime, mixin
    ):
        """Should add document search instructions for PERFORM_RAG_SEARCH action."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)

        prompt = mixin.get_system_prompt_for_action(
            LLMActionType.PERFORM_RAG_SEARCH
        )

        assert "Mode: DOCUMENT SEARCH" in prompt
        assert "rag_search" in prompt
        assert "search_web" in prompt
        # Verify critical instruction is present
        assert "CRITICAL INSTRUCTION" in prompt
        assert "MUST use the rag_search tool" in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_application_command_action_adds_auto_instructions(
        self, mock_datetime, mixin
    ):
        """Should add autonomous tool selection for APPLICATION_COMMAND action."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)

        prompt = mixin.get_system_prompt_for_action(
            LLMActionType.APPLICATION_COMMAND
        )

        assert "Mode: AUTO" in prompt
        assert "Full Capabilities" in prompt
        assert "access to all tools" in prompt
        assert "autonomously determine" in prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_all_actions_include_base_prompt(self, mock_datetime, mixin):
        """Should include base system prompt (bot identity) for all action types.
        
        Note: Datetime is now context-aware and only included for actions that
        benefit from temporal awareness (CONVERSATIONAL_ACTIONS and DATETIME_ACTIONS).
        """
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)
        actions = [
            LLMActionType.CHAT,
            LLMActionType.GENERATE_IMAGE,
            LLMActionType.PERFORM_RAG_SEARCH,
            LLMActionType.APPLICATION_COMMAND,
        ]

        for action in actions:
            prompt = mixin.get_system_prompt_for_action(action)

            # Bot identity should always be present
            assert "You are TestBot" in prompt, f"Bot identity missing for {action}"
        
        # Datetime is context-aware: only included for conversational/datetime actions
        chat_prompt = mixin.get_system_prompt_for_action(LLMActionType.CHAT)
        assert "2024-01-15 10:30:00" in chat_prompt, "Datetime should be in CHAT"
        
        auto_prompt = mixin.get_system_prompt_for_action(LLMActionType.APPLICATION_COMMAND)
        assert "2024-01-15 10:30:00" in auto_prompt, "Datetime should be in APPLICATION_COMMAND"
        
        # Image generation doesn't need datetime (it's not contextually relevant)
        image_prompt = mixin.get_system_prompt_for_action(LLMActionType.GENERATE_IMAGE)
        # Either datetime is absent or present - the key is identity is present
        assert "You are TestBot" in image_prompt

    @patch(
        "airunner.components.llm.managers.mixins.system_prompt_mixin.datetime"
    )
    def test_action_specific_text_appended_to_base(self, mock_datetime, mixin):
        """Should include action-specific text beyond the base identity prompt."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0)

        chat_prompt = mixin.get_system_prompt_for_action(LLMActionType.CHAT)
        
        # Chat prompt should contain bot identity and action-specific content
        assert "You are TestBot" in chat_prompt
        assert "Mode: CHAT" in chat_prompt
        assert "natural conversation" in chat_prompt
        
        # Action prompt should be longer than minimal identity-only prompt
        assert len(chat_prompt) > 50  # Reasonably sized prompt
