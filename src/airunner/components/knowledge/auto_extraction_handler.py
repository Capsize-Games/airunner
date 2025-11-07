"""
Auto-extraction handler - triggers knowledge extraction after conversations.

This module listens for completed LLM responses and triggers automatic
knowledge extraction when enabled.
"""

from typing import Dict, Optional

from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.enums import SignalCode


class AutoExtractionHandler(MediatorMixin, SettingsMixin):
    """
    Handles automatic knowledge extraction after LLM responses.

    Listens for LLM_TEXT_STREAMED_SIGNAL with is_end_of_message=True
    and triggers knowledge extraction if auto_extract_knowledge is enabled.
    """

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

        # Track conversation state
        self._current_user_message: Optional[str] = None
        self._current_bot_response: str = ""
        self._current_conversation_id: Optional[int] = None

        # Register signal handlers
        self.register(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, self.on_llm_request
        )
        self.register(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL, self.on_llm_text_streamed
        )

        self.logger.info("AutoExtractionHandler initialized")

    def on_llm_request(self, data: Dict):
        """
        Capture the user's message when a request is made.

        Args:
            data: Request data containing the user's message
        """
        try:
            # Extract user message from request
            request_data = data.get("request_data", {})
            prompt = request_data.get("prompt", "")

            # Store for extraction later
            self._current_user_message = prompt
            self._current_bot_response = ""

            # Try to get conversation ID from context
            # This might be in different places depending on the flow
            self._current_conversation_id = data.get("conversation_id")

            self.logger.debug(
                f"Captured user message for extraction: {prompt[:100]}..."
            )

        except Exception as e:
            self.logger.error(
                f"Error capturing user message: {e}", exc_info=True
            )

    def on_llm_text_streamed(self, data: Dict):
        """
        Handle streamed LLM responses.

        Args:
            data: Response data with:
                - response: LLMResponse object
        """
        try:
            response = data.get("response")
            if not response:
                return

            # Accumulate bot response text
            if hasattr(response, "text") and response.text:
                self._current_bot_response += response.text

            # Check if this is the end of the message
            if (
                hasattr(response, "is_end_of_message")
                and response.is_end_of_message
            ):
                self._on_conversation_turn_complete()

        except Exception as e:
            self.logger.error(
                f"Error handling streamed text: {e}", exc_info=True
            )

    def _on_conversation_turn_complete(self):
        """
        Called when a conversation turn is complete.

        Triggers knowledge extraction if auto_extract_knowledge is enabled.
        """
        try:
            # Check if auto-extraction is enabled
            if not self.llm_generator_settings.auto_extract_knowledge:
                self.logger.debug("Auto-extraction disabled - skipping")
                return

            # Verify we have both messages
            if (
                not self._current_user_message
                or not self._current_bot_response
            ):
                self.logger.debug(
                    f"Incomplete conversation turn - "
                    f"user: {bool(self._current_user_message)}, "
                    f"bot: {bool(self._current_bot_response)}"
                )
                return

            # Don't extract from very short exchanges (likely greetings/acknowledgments)
            if (
                len(self._current_user_message) < 10
                or len(self._current_bot_response) < 10
            ):
                self.logger.debug("Conversation turn too short for extraction")
                return

            self.logger.info(
                f"Conversation turn complete - triggering knowledge extraction "
                f"(user: {len(self._current_user_message)} chars, "
                f"bot: {len(self._current_bot_response)} chars)"
            )

            # Trigger extraction
            self.emit_signal(
                SignalCode.KNOWLEDGE_EXTRACT_FROM_CONVERSATION,
                {
                    "user_message": self._current_user_message,
                    "bot_response": self._current_bot_response,
                    "conversation_id": self._current_conversation_id,
                },
            )

            # Reset state for next turn
            self._current_user_message = None
            self._current_bot_response = ""

        except Exception as e:
            self.logger.error(
                f"Error in conversation turn completion: {e}", exc_info=True
            )
