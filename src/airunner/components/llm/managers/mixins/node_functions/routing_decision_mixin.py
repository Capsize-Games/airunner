"""Routing and duplicate-tool detection for node-function orchestration."""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from langchain_core.messages import BaseMessage

from airunner.settings import AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW

if TYPE_CHECKING:
    from airunner.components.llm.managers.workflow_manager import WorkflowState


class RoutingDecisionMixin:
    """Provide routing logic for post-model and post-tool workflow steps."""

    def _route_after_model(self, state: "WorkflowState") -> str:
        """Route to tools if the model made tool calls, otherwise end."""
        last_message = state["messages"][-1]
        has_tool_calls = self._has_tool_calls(last_message)

        self._log_routing_debug(last_message, state["messages"])

        if has_tool_calls:
            if self._is_duplicate_tool_call(last_message, state["messages"]):
                return "force_response"

            self._log_tool_call_info(last_message, state["messages"])
            return "tools"

        tool_messages = self._get_current_turn_tool_messages(state["messages"])
        if tool_messages:
            last_tool_msg = tool_messages[-1]
            tool_content = str(getattr(last_tool_msg, "content", ""))
            if tool_content.startswith("ERROR:") and "Cannot use" in tool_content:
                self.logger.warning(
                    "[ROUTE DEBUG] Tool error requires corrective tool call"
                )

        return "end"

    def _route_after_tools(self, state: "WorkflowState") -> str:
        """Route after tools execute and decide whether the model responds."""
        current_turn_messages = self._get_current_turn_messages(
            state["messages"]
        )
        tool_messages = self._get_tool_messages(current_turn_messages)

        if not tool_messages:
            return "end"

        no_response_tools = {
            "clear_conversation",
            "emit_signal",
            "toggle_tts",
            "clear_canvas",
            "quit_application",
            "clear_chat_history",
            "delete_conversation",
            "switch_conversation",
            "create_new_conversation",
            "update_conversation_title",
        }
        task_completing_tools = {
            "write_file",
            "complete_todo_item",
        }
        direct_response_tools = set()

        last_tool_msg = tool_messages[-1]
        last_ai_msg = self._get_last_tool_calling_ai_message(
            current_turn_messages
        )
        if not last_ai_msg or not getattr(last_ai_msg, "tool_calls", None):
            return "end"

        for tool_call in last_ai_msg.tool_calls:
            tool_name = tool_call.get("name", "")
            self.logger.info("[ROUTE DEBUG] Checking tool: %s", tool_name)

            if tool_name in no_response_tools:
                continue

            if self._should_return_tool_direct(tool_name):
                self.logger.info(
                    "[ROUTE DEBUG] Tool '%s' is return_direct - routing to "
                    "force_response",
                    tool_name,
                )
                return "force_response"

            if tool_name in direct_response_tools:
                self.logger.info(
                    "[ROUTE DEBUG] Tool '%s' should be synthesized directly",
                    tool_name,
                )
                return "force_response"

            last_tool_content = str(getattr(last_tool_msg, "content", ""))
            tool_succeeded = any(
                indicator in last_tool_content.lower()
                for indicator in (
                    "created",
                    "successfully",
                    "written",
                    "✓",
                    "complete",
                    "done",
                )
            )

            if tool_name in task_completing_tools and tool_succeeded:
                self.logger.info(
                    "[ROUTE DEBUG] Task-completing tool '%s' succeeded - "
                    "forcing response to prevent unnecessary tool calls",
                    tool_name,
                )
                return "force_response"

            if self._should_force_document_tool_response(tool_name):
                self.logger.info(
                    "[ROUTE DEBUG] Document tool '%s' completed - forcing "
                    "response synthesis",
                    tool_name,
                )
                return "force_response"

            max_tool_iterations = 10
            tool_call_count = len(
                [
                    message
                    for message in state["messages"]
                    if getattr(message, "tool_calls", None)
                ]
            )

            if tool_call_count >= max_tool_iterations:
                self.logger.warning(
                    "[ROUTE DEBUG] Max tool iterations (%s) reached - "
                    "forcing response",
                    max_tool_iterations,
                )
                return "force_response"

            self.logger.info(
                "[ROUTE DEBUG] Tool '%s' completed - routing back to model "
                "for next action",
                tool_name,
            )
            return "model"

        self.logger.info(
            "[ROUTE DEBUG] All tools were status-only - ending workflow"
        )
        return "end"

    def _log_routing_debug(
        self,
        last_message: BaseMessage,
        messages: List[BaseMessage],
    ) -> None:
        """Log routing debug information for one workflow step."""
        self.logger.debug("Last message type: %s", type(last_message).__name__)
        self.logger.debug(
            "Has tool_calls attribute: %s",
            hasattr(last_message, "tool_calls"),
        )

        if hasattr(last_message, "tool_calls"):
            self.logger.debug("tool_calls value: %s", last_message.tool_calls)

        if hasattr(last_message, "content"):
            content_preview = (
                last_message.content[:300] if last_message.content else "None"
            )
            self.logger.debug("Message content preview: %s", content_preview)

        tool_messages = self._get_current_turn_tool_messages(messages)
        ai_messages = [
            message
            for message in messages
            if message.__class__.__name__ == "AIMessage"
        ]

        self.logger.debug(
            "Routing: has_tool_calls=%s, message_type=%s",
            self._has_tool_calls(last_message),
            type(last_message).__name__,
        )
        self.logger.debug(
            "Message history: %s AI messages, %s tool results",
            len(ai_messages),
            len(tool_messages),
        )

    def _is_duplicate_tool_call(
        self,
        last_message: BaseMessage,
        messages: List[BaseMessage],
    ) -> bool:
        """Return whether the last tool call duplicates a prior one."""
        tool_messages = self._get_current_turn_tool_messages(messages)
        ai_messages = [
            message
            for message in messages
            if message.__class__.__name__ == "AIMessage"
        ]

        if not tool_messages or len(ai_messages) < 2:
            return False

        previous_tool_calls = self._extract_previous_tool_calls(
            ai_messages,
            max_last_messages=AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW,
        )

        for current_tool_call in last_message.tool_calls:
            if self._check_tool_call_duplicate(
                current_tool_call,
                previous_tool_calls,
                tool_messages,
            ):
                return True

        return False

    def _extract_previous_tool_calls(
        self,
        ai_messages: List[BaseMessage],
        max_last_messages: Optional[int] = None,
    ) -> List[Dict]:
        """Return prior tool calls from previous AI messages only."""
        previous_tool_calls = []
        if max_last_messages is not None and max_last_messages > 0:
            ai_messages = ai_messages[-(max_last_messages + 1) :]

        for index, ai_message in enumerate(ai_messages[:-1]):
            for tool_call in getattr(ai_message, "tool_calls", []) or []:
                previous_tool_calls.append(
                    {
                        "name": tool_call.get("name"),
                        "args": tool_call.get("args", {}),
                        "message_index": index,
                    }
                )
        return previous_tool_calls

    def _check_tool_call_duplicate(
        self,
        current_tool_call: Dict,
        previous_tool_calls: List[Dict],
        tool_messages: List,
    ) -> bool:
        """Return whether one tool call duplicates a previous tool call."""
        current_name = current_tool_call.get("name")
        current_args = current_tool_call.get("args", {})
        current_normalized = self._normalize_args(current_args)

        for previous_tool_call in previous_tool_calls:
            if previous_tool_call["name"] != current_name:
                continue

            previous_normalized = self._normalize_args(
                previous_tool_call["args"]
            )
            if current_normalized == previous_normalized:
                self._log_duplicate_detection(
                    current_name,
                    current_args,
                    tool_messages,
                )
                return True

        return False

    def _normalize_args(self, args: Any) -> Tuple:
        """Convert tool arguments into one comparable normalized shape."""
        if not isinstance(args, dict):
            return str(args)

        items = []
        for key, value in sorted(args.items()):
            if isinstance(value, dict):
                value = self._normalize_args(value)
            elif isinstance(value, list):
                value = tuple(value)
            items.append((key, value))
        return tuple(items)

    def _log_duplicate_detection(
        self,
        tool_name: str,
        tool_args: Dict,
        tool_messages: List,
    ) -> None:
        """Log duplicate tool-call detection details."""
        self.logger.error("🔁 DUPLICATE TOOL CALL DETECTED!")
        self.logger.error("   Tool: %s", tool_name)
        self.logger.error("   Arguments: %s", tool_args)
        self.logger.error(
            "   This exact tool call was already executed in a previous turn."
        )
        self.logger.error(
            "   Model is stuck in a loop - forcing conversational response."
        )

        if tool_messages:
            last_tool_content = (
                tool_messages[-1].content if tool_messages[-1].content else ""
            )
            self.logger.info(
                "   Previous tool results available: %s chars",
                len(last_tool_content),
            )

    def _log_tool_call_info(
        self,
        last_message: BaseMessage,
        messages: List[BaseMessage],
    ) -> None:
        """Log the tool calls and the latest tool result preview."""
        tool_names = [tool_call.get("name") for tool_call in last_message.tool_calls]
        self.logger.info(
            "Model requested %s tool calls: %s",
            len(last_message.tool_calls),
            tool_names,
        )

        tool_messages = self._get_current_turn_tool_messages(messages)
        if tool_messages and hasattr(tool_messages[-1], "content"):
            result_content = tool_messages[-1].content
            result_preview = result_content[:200] if result_content else "No content"
            self.logger.info(
                "📋 Previous tool result length: %s chars, preview: %s...",
                len(result_content),
                result_preview,
            )