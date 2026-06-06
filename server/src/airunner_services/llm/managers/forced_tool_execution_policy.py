"""Forced-tool execution policy for workflow tool runs."""

from __future__ import annotations

import uuid
from typing import Any, TYPE_CHECKING

from langchain_core.messages import AIMessage, ToolMessage

if TYPE_CHECKING:
    from airunner_services.llm.workflow_manager import WorkflowState


class ForcedToolExecutionPolicy:
    """Apply forced-tool constraints before and after ToolNode execution."""

    def __init__(self, owner: Any):
        self._owner = owner

    def prepare(
        self,
        state: "WorkflowState",
        tool_calls: list[dict],
    ) -> tuple["WorkflowState", list[dict], "WorkflowState | None"]:
        """Return the execution plan for the current forced-tool state."""
        force_tool = getattr(self._owner, "_force_tool", None)
        if not force_tool:
            return state, tool_calls, None

        first_tool = tool_calls[0].get("name") if tool_calls else None
        if first_tool != force_tool:
            return (
                state,
                tool_calls,
                self._build_violation_state(
                    tool_calls,
                    first_tool,
                    force_tool,
                ),
            )
        if len(tool_calls) == 1:
            return state, tool_calls, None

        discarded = [tool_call.get("name") for tool_call in tool_calls[1:]]
        self._owner.logger.warning(
            "Force tool active: executing only '%s', discarding parallel "
            "calls: %s",
            force_tool,
            discarded,
        )
        filtered_calls = [tool_calls[0]]
        messages = list(state["messages"])
        last_message = messages[-1]
        messages[-1] = AIMessage(
            content=last_message.content,
            tool_calls=filtered_calls,
        )
        return {**state, "messages": messages}, filtered_calls, None

    def complete(self, tool_calls: list[dict]) -> None:
        """Apply post-execution force-tool cleanup and rebinding rules."""
        force_tool = getattr(self._owner, "_force_tool", None)
        if not force_tool:
            return

        executed_tool = tool_calls[0].get("name") if tool_calls else None
        if executed_tool != force_tool:
            return

        next_tool = self._owner._get_next_workflow_tool(executed_tool)
        if next_tool:
            self._owner.logger.info(
                "Workflow sequence: '%s' done, now enforcing '%s'",
                executed_tool,
                next_tool,
            )
            self._owner._force_tool = next_tool
            self._owner._tool_choice = {
                "type": "function",
                "function": {"name": next_tool},
            }
            if hasattr(self._owner, "_bind_tools_to_model"):
                self._owner._bind_tools_to_model()
            return

        self._owner.logger.info(
            "Clearing force_tool '%s' after successful execution",
            force_tool,
        )
        self._owner._force_tool = None
        self._owner._tool_choice = None
        if hasattr(self._owner, "_unbind_tools_from_model"):
            self._owner._unbind_tools_from_model()

    def _build_violation_state(
        self,
        tool_calls: list[dict],
        called_tool: str | None,
        force_tool: str,
    ) -> "WorkflowState":
        """Return an error tool result when the wrong tool was called."""
        self._owner.logger.error(
            "Force tool violation: model called '%s' but must call '%s' "
            "first",
            called_tool,
            force_tool,
        )
        error_msg = (
            f"ERROR: You must call '{force_tool}' first.\n\n"
            f"You tried to call '{called_tool}', but the workflow requires "
            f"calling '{force_tool}' before any other tool.\n\n"
            f"Call {force_tool}('coding', 'your task description') NOW."
        )
        tool_call_id = tool_calls[0].get("id", str(uuid.uuid4()))
        error_result = ToolMessage(
            content=error_msg,
            tool_call_id=tool_call_id,
            name=called_tool,
        )
        return {"messages": [error_result]}
