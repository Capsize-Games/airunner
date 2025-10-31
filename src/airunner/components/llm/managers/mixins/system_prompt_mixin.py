"""System prompt generation for LLM models.

This mixin provides:
- Base system prompt construction
- Action-specific prompt customization
- Personality integration (disabled for precision tools)
- Timestamp inclusion
- Mood system integration (disabled for precision tools)
- Context-aware prompt selection (precision vs conversational)
"""

from datetime import datetime
from typing import Optional, List

from airunner.enums import LLMActionType
from airunner.components.llm.core.tool_registry import ToolCategory


# Precision-focused system prompt for mathematical/technical tools
PRECISION_SYSTEM_PROMPT = """You are a precise technical assistant focused on accuracy.

Current date and time: {datetime}

CRITICAL: Provide exact, deterministic answers. Do not add creative flair or personality.
Focus entirely on solving the problem correctly using the available tools when needed."""


class SystemPromptMixin:
    """Mixin for LLM system prompt generation."""

    def _should_use_precision_prompt(
        self, tool_categories: Optional[List] = None
    ) -> bool:
        """Determine if precision prompt should be used instead of personality.

        Args:
            tool_categories: List of ToolCategory values being used

        Returns:
            True if precision tools are being used (MATH, etc.)
        """
        if not tool_categories:
            return False

        # Convert string names to ToolCategory if needed
        category_values = []
        for cat in tool_categories:
            if isinstance(cat, str):
                # Try to match by value
                for tc in ToolCategory:
                    if tc.value == cat:
                        category_values.append(tc)
                        break
            else:
                category_values.append(cat)

        # Use precision prompt for MATH tools
        precision_categories = {ToolCategory.MATH}
        return any(cat in precision_categories for cat in category_values)

    def get_system_prompt_with_context(
        self,
        action: LLMActionType,
        tool_categories: Optional[List] = None,
    ) -> str:
        """Generate system prompt based on context (precision vs conversational).

        Args:
            action: The type of action being performed
            tool_categories: Optional list of tool categories being used

        Returns:
            Appropriate system prompt for the context
        """
        # Use precision prompt for math/technical tools
        if self._should_use_precision_prompt(tool_categories):
            now = datetime.now()
            return PRECISION_SYSTEM_PROMPT.format(
                datetime=now.strftime("%Y-%m-%d %H:%M:%S")
            )

        # Otherwise use personality-based prompt
        return self.get_system_prompt_for_action(action)

    @property
    def system_prompt(self) -> str:
        """Generate the system prompt for the LLM.

        Returns:
            Complete system prompt string
        """
        parts = []

        if hasattr(self, "chatbot") and self.chatbot:
            parts.append(
                f"You are {self.chatbot.botname}, a helpful AI assistant."
            )

            if (
                hasattr(self.chatbot, "personality")
                and self.chatbot.personality
            ):
                parts.append(f"Personality: {self.chatbot.personality}")
        else:
            parts.append("You are a helpful AI assistant.")

        now = datetime.now()
        parts.append(
            f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if (
            self.llm_settings.use_chatbot_mood
            and hasattr(self, "chatbot")
            and self.chatbot
            and hasattr(self.chatbot, "use_mood")
            and self.chatbot.use_mood
        ):
            parts.append(
                f"\nYou have access to an update_mood tool. "
                f"Every {self.llm_settings.update_mood_after_n_turns} conversation turns, "
                f"reflect on the conversation and update your emotional state by calling the "
                f"update_mood tool with a one-word emotion (e.g., happy, sad, excited, thoughtful, "
                f"confused) and a matching emoji (e.g., 😊, 😢, 🤔, 😐). "
                f"Your mood should reflect your personality and the context of the conversation."
            )

        return "\n\n".join(parts)

    def get_system_prompt_for_action(self, action: LLMActionType) -> str:
        """Generate a system prompt tailored to the specific action type.

        Args:
            action: The type of action being performed

        Returns:
            System prompt with action-specific instructions
        """
        base_prompt = self.system_prompt

        if action == LLMActionType.CHAT:
            base_prompt += (
                "\n\nMode: CHAT"
                "\nFocus on natural conversation. You may use conversation management tools "
                "(clear_conversation, toggle_tts) and data storage tools as needed, but avoid "
                "image generation or RAG search unless explicitly requested by the user."
            )

        elif action == LLMActionType.GENERATE_IMAGE:
            base_prompt += (
                "\n\nMode: IMAGE GENERATION"
                "\nYour primary focus is generating images. Use the generate_image tool "
                "to create images based on user descriptions. You may also use canvas tools "
                "(clear_canvas, open_image) to manage the workspace."
            )

        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            base_prompt += (
                "\n\nMode: DOCUMENT SEARCH"
                "\nYour primary focus is searching through uploaded documents. Use the rag_search "
                "tool to find relevant information in the document database. You may also use "
                "search_web for supplementary internet searches."
            )

        elif action == LLMActionType.APPLICATION_COMMAND:
            base_prompt += (
                "\n\nMode: AUTO (Full Capabilities)"
                "\nYou have access to all tools and should autonomously determine which tools "
                "to use based on the user's request. Analyze the intent and choose the most "
                "appropriate tools to fulfill the user's needs."
            )

        return base_prompt
