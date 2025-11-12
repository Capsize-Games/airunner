"""Manages loading and formatting of conversation history."""

from typing import Any, Dict, List, Optional

from airunner.components.llm.data.conversation import Conversation
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
                self.logger.info(f"Current conversation ID: {conversation.id}")
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

        self.logger.debug(
            f"Loading conversation history for ID: {getattr(conversation, 'id', None)} (max: {max_messages})"
        )
        conversation_id = getattr(conversation, "id", None)
        try:
            raw_messages = getattr(conversation, "value", None)
            if not isinstance(raw_messages, list):
                self.logger.warning(
                    f"Conversation {conversation_id} has invalid message data (not a list): {type(raw_messages)}"
                )
                return []
            if not raw_messages:
                self.logger.info(f"Conversation {conversation_id} is empty.")
                return []

            # Apply max_messages limit
            if len(raw_messages) > max_messages:
                raw_messages = raw_messages[-max_messages:]

            formatted_messages: List[Dict[str, Any]] = []
            for msg_idx, msg_obj in enumerate(raw_messages):
                if not isinstance(msg_obj, dict):
                    self.logger.warning(
                        f"Skipping invalid message object (not a dict) in conversation {conversation_id}: {msg_obj}"
                    )
                    continue

                # Skip tool call metadata messages (for debugging only, not for display)
                if msg_obj.get("metadata_type") in (
                    "tool_calls",
                    "tool_result",
                ):
                    self.logger.debug(
                        f"Skipping tool metadata message: {msg_obj.get('role')}"
                    )
                    continue

                # Also skip by role for backward compatibility
                role = msg_obj.get("role")
                if role in ("tool_calls", "tool_result"):
                    self.logger.debug(
                        f"Skipping tool call message with role: {role}"
                    )
                    continue

                is_bot = role == "assistant"

                # Name extraction logic: prefer message-level, then conversation-level, then default
                if is_bot:
                    name = (
                        msg_obj.get("bot_name")
                        or getattr(conversation, "chatbot_name", None)
                        or "Bot"
                    )
                else:
                    name = (
                        msg_obj.get("user_name")
                        or getattr(conversation, "user_name", None)
                        or "User"
                    )

                # Content extraction logic
                content = msg_obj.get("content")
                if content is None:
                    # Try to extract from blocks if present
                    blocks = msg_obj.get("blocks")
                    if isinstance(blocks, list) and blocks:
                        for block in blocks:
                            if isinstance(block, dict) and "text" in block:
                                content = block["text"]
                                self.logger.debug(
                                    f"Extracted content from blocks: {content[:50]}..."
                                )
                                break
                        if content is None:
                            content = ""
                            self.logger.warning(
                                f"No text found in blocks for message {msg_idx}"
                            )
                    else:
                        content = ""
                        self.logger.warning(
                            f"No blocks found for message {msg_idx}"
                        )
                else:
                    self.logger.debug(
                        f"Content found directly in message {msg_idx}: {content[:50]}..."
                    )

                formatted_msg = {
                    "name": name,
                    "content": content,
                    "is_bot": is_bot,
                    "id": msg_idx,  # Simple index within this loaded history
                }
                # Pass through mood/emoji fields if present
                for key in ("bot_mood", "bot_mood_emoji", "user_mood"):
                    if key in msg_obj:
                        formatted_msg[key] = msg_obj[key]
                formatted_messages.append(formatted_msg)
            self.logger.info(
                f"Successfully loaded {len(formatted_messages)} messages for conversation ID: {conversation_id}"
            )
            return formatted_messages

        except Exception as e:
            self.logger.error(
                f"Error loading conversation history for ID {conversation_id}: {e}",
                exc_info=True,
            )
            return []
