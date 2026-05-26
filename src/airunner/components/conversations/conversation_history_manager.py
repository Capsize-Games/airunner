"""Manages loading and formatting of conversation history."""

from typing import Any, Dict, List, Optional

from airunner_model.models.conversation import Conversation
from airunner_model.conversation_history_formatter import (
    load_formatted_conversation_history,
)
from airunner.components.llm.utils.thinking_parser import (
    normalize_thinking_content,
    strip_stored_thinking_prefix,
)
from airunner.components.llm.utils.gpt_oss_parser import (
    has_gpt_oss_markup,
    parse_gpt_oss_response,
)
from airunner.components.llm.utils.persistence_filters import (
    is_internal_stage_message_dict,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ConversationHistoryManager:
    """Handles fetching and formatting of conversation history.

    This manager provides a centralized way to access conversation data,
    decoupling UI components and other services from the specifics of
    how conversations are stored or whether an LLM agent is active.
    """

    def __init__(self) -> None:
        """Initializes the ConversationHistoryManager."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def get_current_conversation(self) -> Optional[Conversation]:
        """Fetches the current conversation.

        Returns:
            Optional[Conversation]: The current conversation object, or None
                                     if no current conversation exists.
        """
        conversations = Conversation.objects.filter_by(current=True)
        if len(conversations) == 0:
            self.logger.info("No current conversation found.")
            return None
        self.logger.debug("Fetching the current conversation.")
        try:
            conversation = conversations[0]
            if conversation:
                self.logger.debug(
                    f"Current conversation ID: {conversation.id}"
                )
                return conversation
            self.logger.info("No current conversation found.")
            return None
        except Exception as e:
            self.logger.error(
                f"Error fetching current conversation: {e}",
                exc_info=True,
            )
            return None

    def get_most_recent_conversation_id(self) -> Optional[int]:
        """Fetches the ID of the most recent conversation.

        Returns:
            Optional[int]: The ID of the most recent conversation, or None
                           if no conversations exist.
        """
        self.logger.debug("Fetching the most recent conversation ID.")
        try:
            conversation = Conversation.most_recent()
            if conversation:
                self.logger.info(
                    f"Most recent conversation ID: {conversation.id}"
                )
                return conversation.id
            self.logger.info("No conversations found.")
            return None
        except Exception as e:
            self.logger.error(
                f"Error fetching most recent conversation ID: {e}",
                exc_info=True,
            )
            return None

    def load_conversation_history(
        self,
        conversation: Optional[Conversation] = None,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
    ) -> List[Dict[str, Any]]:
        """Load and format one conversation history for GUI consumers."""
        if conversation is None and conversation_id is not None:
            conversation = Conversation.objects.filter_by_first(
                id=conversation_id
            )
            if conversation is None:
                self.logger.warning(
                    f"Conversation {conversation_id} not found. Returning empty history."
                )
                return []
        elif conversation is None:
            conversation = self.get_current_conversation()

        if conversation is None:
            conversation = Conversation.most_recent()
            if conversation is None:
                self.logger.warning(
                    "No conversation found. Returning empty history."
                )
                return []
        return load_formatted_conversation_history(
            logger=self.logger,
            conversation=conversation,
            max_messages=max_messages,
            normalize_thinking_content=normalize_thinking_content,
            strip_stored_thinking_prefix=strip_stored_thinking_prefix,
            has_gpt_oss_markup=has_gpt_oss_markup,
            parse_gpt_oss_response=parse_gpt_oss_response,
            skip_message=is_internal_stage_message_dict,
            include_tool_status_metadata=True,
            include_thinking_metadata=True,
        )
