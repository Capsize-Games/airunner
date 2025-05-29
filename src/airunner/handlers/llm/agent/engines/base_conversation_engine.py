"""
BaseConversationEngine: Unified base class for all conversation/memory-aware engines/tools.

Provides standardized message appending, conversation state updating, and memory sync logic.
"""

import datetime
from typing import Any, Optional


class BaseConversationEngine:
    """
    Base class for engines/tools that interact with conversation and memory.
    """

    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self._logger = getattr(agent, "logger", None)

    def append_conversation_messages(
        self,
        conversation,
        user_message: str,
        assistant_message: Optional[str] = None,
    ) -> None:
        """
        Append user and assistant messages to the conversation value.
        Args:
            conversation: The Conversation object.
            user_message (str): The user's message.
            assistant_message (Optional[str]): The assistant's message (if any).
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conversation.value.append(
            {
                "role": "user",
                "name": self.agent.username,
                "content": user_message,
                "timestamp": now,
            }
        )
        if assistant_message is not None:
            conversation.value.append(
                {
                    "role": "assistant",
                    "name": self.agent.botname,
                    "content": assistant_message,
                    "timestamp": now,
                }
            )
        if self._logger:
            self._logger.debug(
                f"[BaseConversationEngine] Appended user/assistant messages: user='{user_message}', assistant='{assistant_message}'"
            )

    def update_conversation_state(self, conversation) -> None:
        """
        Update conversation state and chat memory after a turn.
        Args:
            conversation: The Conversation object.
        """
        Conversation = type(conversation)
        Conversation.objects.update(
            self.agent.conversation_id,
            value=conversation.value,
            last_analyzed_message_id=len(conversation.value) - 1,
            last_analysis_time=datetime.datetime.now(),
        )
        if getattr(self.agent, "chat_memory", None) is not None:
            chat_messages = []
            for msg in conversation.value:
                if hasattr(msg, "blocks"):
                    chat_messages.append(msg)
                else:
                    content = msg.get("content", "")
                    chat_messages.append(
                        self.agent._make_chat_message(
                            role=msg.get("role", "user"),
                            content=content,
                        )
                    )
            self.agent.chat_memory.set(chat_messages)
        if hasattr(self.agent, "_sync_memory_to_all_engines"):
            self.agent._sync_memory_to_all_engines()
