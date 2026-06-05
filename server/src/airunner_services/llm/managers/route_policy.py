"""Route-policy helpers for LangGraph workflow nodes."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from langchain_core.messages import AIMessage

if TYPE_CHECKING:
    from airunner_services.llm.workflow_manager import WorkflowState


class RoutePolicy:
    """Compute post-node routing decisions for workflow execution."""

    NO_RESPONSE_TOOLS = {
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
    TASK_COMPLETING_TOOLS = {
        "write_file",
        "complete_todo_item",
    }

    def __init__(self, owner: Any):
        self._owner = owner

    def after_model(self, state: "WorkflowState") -> str:
        """Route to tools, forced response, or end after model output."""
        last_message = state["messages"][-1]
        self._owner._log_routing_debug(last_message, state["messages"])
        if self._owner._has_tool_calls(last_message):
            if self._owner._is_duplicate_tool_call(
                last_message,
                state["messages"],
            ):
                return "force_response"
            self._owner._log_tool_call_info(last_message, state["messages"])
            return "tools"

        self._log_ignored_tool_error(last_message, state)
        return "end"

    def after_tools(self, state: "WorkflowState") -> str:
        """Route to model, forced response, or end after tool execution."""
        tool_messages = self._owner._get_tool_messages(state["messages"])
        if not tool_messages:
            return "end"

        last_ai_msg = self._get_last_ai_message(state)
        if last_ai_msg is None:
            return "end"

        last_tool_msg = tool_messages[-1]
        force_tool = getattr(self._owner, "_force_tool", None)
        for tool_call in last_ai_msg.tool_calls:
            route = self._route_for_tool_call(
                tool_call.get("name", ""),
                str(getattr(last_tool_msg, "content", "")),
                force_tool,
                state,
            )
            if route is not None:
                return route

        self._owner.logger.info(
            "[ROUTE DEBUG] All tools were status-only - ending workflow"
        )
        return "end"

    def _log_ignored_tool_error(
        self,
        last_message: Any,
        state: "WorkflowState",
    ) -> None:
        """Log when the model answers after a corrective tool error."""
        tool_messages = self._owner._get_tool_messages(state["messages"])
        if not tool_messages:
            return

        last_tool_msg = tool_messages[-1]
        tool_content = str(getattr(last_tool_msg, "content", ""))
        if not (
            tool_content.startswith("ERROR:") and "Cannot use" in tool_content
        ):
            return

        response_content = getattr(last_message, "content", "")
        self._owner.logger.warning(
            "[ROUTE DEBUG] Model ignored tool ERROR and responded with "
            "text: %s",
            response_content[:200],
        )

    def _get_last_ai_message(
        self,
        state: "WorkflowState",
    ) -> AIMessage | None:
        """Return the most recent AI message with tool calls."""
        ai_messages = [
            message
            for message in state["messages"]
            if isinstance(message, AIMessage)
        ]
        if not ai_messages:
            return None

        last_ai_msg = ai_messages[-1]
        if not getattr(last_ai_msg, "tool_calls", None):
            return None
        return last_ai_msg

    def _route_for_tool_call(
        self,
        tool_name: str,
        last_tool_content: str,
        force_tool: str | None,
        state: "WorkflowState",
    ) -> str | None:
        """Return a route decision for one executed tool."""
        self._owner.logger.info("[ROUTE DEBUG] Checking tool: %s", tool_name)
        if tool_name in self.NO_RESPONSE_TOOLS:
            return None
        if self._owner._should_return_tool_direct(tool_name):
            self._owner.logger.info(
                "[ROUTE DEBUG] Tool '%s' is return_direct - routing to "
                "force_response",
                tool_name,
            )
            return "force_response"
        if (
            force_tool
            and force_tool != "search_web"
            and tool_name == force_tool
        ):
            self._owner.logger.info(
                "[ROUTE DEBUG] Forced tool '%s' completed - routing to "
                "force_response",
                tool_name,
            )
            return "force_response"
        if self._completed_task(tool_name, last_tool_content):
            self._owner.logger.info(
                "[ROUTE DEBUG] Task-completing tool '%s' succeeded - forcing "
                "response to prevent unnecessary tool calls",
                tool_name,
            )
            return "force_response"
        if self._tool_call_count(state) >= 10:
            self._owner.logger.warning(
                "[ROUTE DEBUG] Max tool iterations (10) reached - forcing "
                "response"
            )
            return "force_response"

        self._owner.logger.info(
            "[ROUTE DEBUG] Tool '%s' completed - routing back to model for "
            "next action",
            tool_name,
        )
        return "model"

    def _completed_task(self, tool_name: str, tool_content: str) -> bool:
        """Return True when a task-completing tool clearly succeeded."""
        if tool_name not in self.TASK_COMPLETING_TOOLS:
            return False

        success_indicators = (
            "created",
            "successfully",
            "written",
            "✓",
            "complete",
            "done",
        )
        return any(
            indicator in tool_content.lower()
            for indicator in success_indicators
        )

    @staticmethod
    def _tool_call_count(state: "WorkflowState") -> int:
        """Return the number of AI messages that carried tool calls."""
        return len(
            [
                message
                for message in state["messages"]
                if getattr(message, "tool_calls", None)
            ]
        )
