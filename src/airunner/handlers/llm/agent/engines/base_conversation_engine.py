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
        Always store with both 'content' and 'blocks' fields for compatibility.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conversation.value.append(
            {
                "role": "user",
                "name": self.agent.username,
                "content": user_message,
                "timestamp": now,
                "blocks": [{"block_type": "text", "text": user_message}],
            }
        )
        if assistant_message is not None:
            conversation.value.append(
                {
                    "role": "assistant",
                    "name": self.agent.botname,
                    "content": assistant_message,
                    "timestamp": now,
                    "blocks": [
                        {"block_type": "text", "text": assistant_message}
                    ],
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

    def append_message_and_persist(
        self,
        conversation: Any,
        role: str,
        content: str,
        name: Optional[str] = None,
        tool_call: bool = False,
    ) -> None:
        """
        Append a message (user, assistant, or tool) to both chat_memory and conversation.value, and persist.
        Args:
            conversation: The Conversation object.
            role: 'user', 'assistant', or 'tool'.
            content: The message content.
            name: The name to use (username, botname, or tool name).
            tool_call: If True, treat as a tool message.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if name is None:
            if role == "user":
                name = getattr(self.agent, "username", "User")
            elif role == "assistant":
                name = getattr(self.agent, "botname", "Assistant")
            else:
                name = "Tool"
        msg_dict = {
            "role": role,
            "name": name,
            "content": content,
            "timestamp": now,
            "blocks": [{"block_type": "text", "text": content}],
        }
        conversation.value.append(msg_dict)
        # Add to chat_memory if available
        if hasattr(self.agent, "chat_memory") and self.agent.chat_memory:
            from llama_index.core.base.llms.types import (
                ChatMessage,
                MessageRole,
            )

            role_map = {
                "user": MessageRole.USER,
                "assistant": MessageRole.ASSISTANT,
                "tool": MessageRole.TOOL,
            }
            chat_msg = ChatMessage(
                content=content, role=role_map.get(role, MessageRole.USER)
            )
            self.agent.chat_memory.put(chat_msg)
        # Persist conversation state
        if hasattr(self.agent, "_update_conversation_state"):
            self.agent._update_conversation_state(conversation)
        if self._logger:
            self._logger.debug(
                f"[BaseConversationEngine] Appended and persisted message: role='{role}', content='{content[:40]}', tool_call={tool_call}"
            )
