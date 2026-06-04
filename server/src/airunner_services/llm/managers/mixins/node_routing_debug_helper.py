"""Routing debug helpers for node functions."""

from __future__ import annotations

from typing import Dict, List, Optional

from langchain_core.messages import BaseMessage

from airunner_services.llm.tool_call_identity import tool_call_identity_key
from airunner_services.settings import AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW


class NodeRoutingDebugHelper:
    """Handle routing diagnostics and duplicate tool-call checks."""

    def __init__(self, owner) -> None:
        """Store the owning workflow manager."""
        self._owner = owner

    def log_routing_debug(
        self,
        last_message: BaseMessage,
        messages: List[BaseMessage],
    ) -> None:
        """Log the routing state for one workflow turn."""
        forced_helper = self._owner._get_forced_response_helper()
        self._owner.logger.debug("Last message type: %s", type(last_message).__name__)
        self._owner.logger.debug(
            "Has tool_calls attribute: %s",
            hasattr(last_message, "tool_calls"),
        )
        if hasattr(last_message, "tool_calls"):
            self._owner.logger.debug("tool_calls value: %s", last_message.tool_calls)
        if hasattr(last_message, "content"):
            content_preview = last_message.content[:300] if last_message.content else "None"
            self._owner.logger.debug("Message content preview: %s", content_preview)
        tool_messages = forced_helper.get_tool_messages(messages)
        ai_messages = [
            message for message in messages if message.__class__.__name__ == "AIMessage"
        ]
        self._owner.logger.debug(
            "Routing: has_tool_calls=%s, message_type=%s",
            forced_helper.has_tool_calls(last_message),
            type(last_message).__name__,
        )
        self._owner.logger.debug(
            "Message history: %s AI messages, %s tool results",
            len(ai_messages),
            len(tool_messages),
        )

    def is_duplicate_tool_call(
        self,
        last_message: BaseMessage,
        messages: List[BaseMessage],
    ) -> bool:
        """Return whether the latest tool call duplicates a recent one."""
        tool_messages = self._owner._get_forced_response_helper().get_tool_messages(
            messages
        )
        ai_messages = [
            message for message in messages if message.__class__.__name__ == "AIMessage"
        ]
        if not tool_messages or len(ai_messages) < 2:
            return False
        previous_tool_calls = self.extract_previous_tool_calls(
            ai_messages,
            max_last_messages=AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW,
        )
        for current_tool_call in last_message.tool_calls:
            if self.check_tool_call_duplicate(
                current_tool_call,
                previous_tool_calls,
                tool_messages,
            ):
                return True
        return False

    @staticmethod
    def extract_previous_tool_calls(
        ai_messages: List[BaseMessage],
        max_last_messages: Optional[int] = None,
    ) -> List[Dict]:
        """Return previous tool-call identities from AI messages."""
        previous_tool_calls = []
        if max_last_messages is not None and max_last_messages > 0:
            ai_messages = ai_messages[-(max_last_messages + 1):]
        for index, ai_message in enumerate(ai_messages[:-1]):
            if not hasattr(ai_message, "tool_calls") or not ai_message.tool_calls:
                continue
            for tool_call in ai_message.tool_calls:
                previous_tool_calls.append(
                    {
                        "name": tool_call.get("name"),
                        "args": tool_call.get("args", {}),
                        "message_index": index,
                    }
                )
        return previous_tool_calls

    def check_tool_call_duplicate(
        self,
        current_tool_call: Dict,
        previous_tool_calls: List[Dict],
        tool_messages: List,
    ) -> bool:
        """Return whether one current tool call matches a prior call."""
        current_name = current_tool_call.get("name")
        current_args = current_tool_call.get("args", {})
        current_identity = tool_call_identity_key(current_tool_call)
        for previous_tool_call in previous_tool_calls:
            if tool_call_identity_key(previous_tool_call) != current_identity:
                continue
            self.log_duplicate_detection(current_name, current_args, tool_messages)
            return True
        return False

    def log_duplicate_detection(
        self,
        tool_name: str,
        tool_args: Dict,
        tool_messages: List,
    ) -> None:
        """Log one duplicate tool-call detection event."""
        self._owner.logger.error("🔁 DUPLICATE TOOL CALL DETECTED!")
        self._owner.logger.error("   Tool: %s", tool_name)
        self._owner.logger.error("   Arguments: %s", tool_args)
        self._owner.logger.error(
            "   This exact tool call was already executed in a previous turn."
        )
        self._owner.logger.error(
            "   Model is stuck in a loop - forcing conversational response."
        )
        if not tool_messages:
            return
        last_tool_content = tool_messages[-1].content if tool_messages[-1].content else ""
        self._owner.logger.info(
            "   Previous tool results available: %s chars",
            len(last_tool_content),
        )

    def log_tool_call_info(
        self,
        last_message: BaseMessage,
        messages: List[BaseMessage],
    ) -> None:
        """Log the requested tool calls and previous tool result preview."""
        tool_names = [tool_call.get("name") for tool_call in last_message.tool_calls]
        self._owner.logger.info(
            "Model requested %s tool calls: %s",
            len(last_message.tool_calls),
            tool_names,
        )
        tool_messages = self._owner._get_forced_response_helper().get_tool_messages(
            messages
        )
        if not tool_messages:
            return
        last_tool_result = tool_messages[-1]
        if not hasattr(last_tool_result, "content"):
            return
        result_content = last_tool_result.content
        result_preview = result_content[:200] if result_content else "No content"
        self._owner.logger.info(
            "📋 Previous tool result length: %s chars, preview: %s...",
            len(result_content),
            result_preview,
        )