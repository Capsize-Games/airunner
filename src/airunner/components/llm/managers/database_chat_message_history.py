"""LangChain message history implementation that persists to the Conversation database."""

import logging
from typing import List, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)

from airunner.components.llm.data.conversation import Conversation


class DatabaseChatMessageHistory(BaseChatMessageHistory):
    """Chat message history that stores messages in the Conversation database.

    This class integrates LangChain's memory system with AI Runner's Conversation
    model, ensuring that all chat messages are properly persisted to the database
    and can be loaded later.
    """

    def __init__(self, conversation_id: Optional[int] = None):
        """Initialize the database chat message history.

        Args:
            conversation_id: Optional conversation ID to load. If None, will use
                           or create the current conversation.
        """
        self.logger = logging.getLogger(__name__)
        self.conversation_id = conversation_id
        self._conversation = None
        self._load_conversation()

    def _load_conversation(self) -> None:
        """Load the conversation from database or create a new one."""
        try:
            if self.conversation_id:
                # Load specific conversation
                self._conversation = Conversation.objects.get(
                    self.conversation_id
                )
            else:
                # Get or create current conversation
                conversations = Conversation.objects.filter_by(current=True)
                if conversations:
                    self._conversation = conversations[0]
                else:
                    # Create new conversation
                    self._conversation = Conversation.create()
                    if self._conversation:
                        self.conversation_id = self._conversation.id
                        Conversation.make_current(self.conversation_id)

            if self._conversation:
                self.conversation_id = self._conversation.id
                self.logger.info(
                    f"Loaded conversation ID: {self.conversation_id}"
                )
            else:
                self.logger.warning("Failed to load or create conversation")

        except Exception as e:
            self.logger.error(
                f"Error loading conversation: {e}", exc_info=True
            )

    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve all messages from the conversation.

        Returns:
            List of LangChain BaseMessage objects
        """
        if not self._conversation:
            return []

        try:
            # Refresh conversation from database
            self._conversation = Conversation.objects.get(self.conversation_id)
            conversation_value = self._conversation.value or []

            # Convert from database format to LangChain messages
            langchain_messages = []
            for msg in conversation_value:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                # Map roles to LangChain message types
                if role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif role in ("assistant", "bot"):
                    langchain_messages.append(AIMessage(content=content))
                elif role == "system":
                    langchain_messages.append(SystemMessage(content=content))

            return langchain_messages

        except Exception as e:
            self.logger.error(f"Error retrieving messages: {e}", exc_info=True)
            return []

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation.

        Args:
            message: LangChain message to add
        """
        if not self._conversation:
            self.logger.error("Cannot add message: no conversation loaded")
            return

        try:
            import datetime

            # Skip ToolMessages - they're internal workflow state
            if message.__class__.__name__ == "ToolMessage":
                self.logger.debug(
                    "Skipping ToolMessage - internal workflow state"
                )
                return

            # Skip AIMessages with tool_calls - they're internal workflow instructions
            if (
                isinstance(message, AIMessage)
                and hasattr(message, "tool_calls")
                and message.tool_calls
            ):
                self.logger.debug(
                    "Skipping AIMessage with tool_calls - internal workflow instruction"
                )
                return

            # Convert LangChain message to database format
            role = "user"
            name = "User"

            if isinstance(message, HumanMessage):
                role = "user"
                name = getattr(self._conversation, "user_name", "User")
            elif isinstance(message, AIMessage):
                role = "assistant"
                name = getattr(self._conversation, "chatbot_name", "Assistant")
            elif isinstance(message, SystemMessage):
                role = "system"
                name = "System"

            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            message_dict = {
                "role": role,
                "name": name,
                "content": message.content,
                "timestamp": now,
                "blocks": [{"block_type": "text", "text": message.content}],
            }

            # Add metadata if present
            if (
                hasattr(message, "additional_kwargs")
                and message.additional_kwargs
            ):
                message_dict.update(message.additional_kwargs)

            # Append to conversation
            if self._conversation.value is None:
                self._conversation.value = []
            self._conversation.value.append(message_dict)

            # Save to database
            Conversation.objects.update(
                self.conversation_id, value=self._conversation.value
            )

            self.logger.debug(
                f"Added {role} message to conversation {self.conversation_id}"
            )

        except Exception as e:
            self.logger.error(f"Error adding message: {e}", exc_info=True)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add multiple messages to the conversation.

        Args:
            messages: List of LangChain messages to add
        """
        for message in messages:
            self.add_message(message)

    def clear(self) -> None:
        """Clear all messages from the conversation."""
        if not self._conversation:
            return

        try:
            self._conversation.value = []
            Conversation.objects.update(self.conversation_id, value=[])
            self.logger.info(f"Cleared conversation {self.conversation_id}")

        except Exception as e:
            self.logger.error(
                f"Error clearing conversation: {e}", exc_info=True
            )
