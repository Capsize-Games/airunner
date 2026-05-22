"""Shared message-state helpers for node-function orchestration."""

from typing import Any, List, Optional

from langchain_core.messages import AIMessage, BaseMessage


class MessageStateMixin:
    """Provide common helpers for inspecting workflow message history."""

    def _has_tool_calls(self, message: BaseMessage) -> bool:
        """Return whether one message requested tool calls."""
        return bool(getattr(message, "tool_calls", None))

    def _get_user_question(self, messages: List[BaseMessage]) -> str:
        """Return the most recent human message content."""
        for message in reversed(messages):
            if message.__class__.__name__ == "HumanMessage":
                content = getattr(message, "content", "")
                return content if isinstance(content, str) else str(content)
        return ""

    def _get_last_tool_calling_ai_message(
        self,
        messages: List[BaseMessage],
    ) -> Optional[AIMessage]:
        """Return the most recent AI message that requested tools."""
        for message in reversed(messages):
            if isinstance(message, AIMessage) and self._has_tool_calls(message):
                return message
        return None

    def _get_current_turn_messages(
        self,
        messages: List[BaseMessage],
    ) -> List[BaseMessage]:
        """Return only the messages for the current user turn."""
        for index in range(len(messages) - 1, -1, -1):
            if messages[index].__class__.__name__ == "HumanMessage":
                return messages[index:]
        return messages

    def _get_tool_messages(self, messages: List[BaseMessage]) -> List[Any]:
        """Return the tool-result messages from one message list."""
        return [
            message
            for message in messages
            if message.__class__.__name__ == "ToolMessage"
        ]

    def _get_current_turn_tool_messages(
        self,
        messages: List[BaseMessage],
    ) -> List[Any]:
        """Return tool-result messages produced during the current turn."""
        return self._get_tool_messages(self._get_current_turn_messages(messages))

    def _combine_tool_results(self, tool_messages: List[Any]) -> str:
        """Combine tool results into one prompt-ready string."""
        combined = ""
        for index, tool_message in enumerate(tool_messages, 1):
            combined += f"\n--- Tool Result {index} ---\n"
            combined += str(getattr(tool_message, "content", ""))
            combined += "\n"
        return combined