"""Builders for autonomous control state-management tools."""

from __future__ import annotations

import json
from typing import Callable, Optional

from langchain_core.tools import tool

from airunner_services.tools.base_tool import BaseTool


def _tool_error(owner: BaseTool, action: str, exc: Exception) -> str:
    """Log and format one autonomous-control tool error."""
    owner.logger.error("Error %s: %s", action, exc)
    return f"Error {action}: {exc}"


def _application_state_result(owner: BaseTool) -> str:
    """Return the current autonomous-control state payload."""
    state = {
        "application": {
            "name": "AI Runner",
            "version": "2.0",
            "mode": "autonomous",
        },
        "llm": {
            "active": True,
            "model": getattr(owner, "active_llm_model_name", "unknown"),
            "tools_count": (
                len(owner.get_all_tools())
                if hasattr(owner, "get_all_tools")
                else 0
            ),
        },
        "conversation": {
            "current_id": getattr(owner, "current_conversation_id", None),
            "has_context": True,
        },
        "capabilities": {
            "image_generation": True,
            "rag": owner.rag_manager is not None,
            "knowledge_base": True,
            "web_access": True,
            "code_execution": True,
        },
    }
    return json.dumps(state, indent=2)


def build_get_application_state_tool(owner: BaseTool) -> Callable:
    """Build the application-state inspection tool."""

    @tool
    def get_application_state() -> str:
        """Get the current application state."""
        try:
            return _application_state_result(owner)
        except Exception as exc:
            return _tool_error(owner, "getting application state", exc)

    return get_application_state


def _schedule_task_result(
    owner: BaseTool,
    task_name: str,
    description: str,
    when: str,
    params: Optional[dict],
) -> str:
    """Schedule one task through the configured action handler."""
    if not owner.dispatch_tool_action(
        "schedule_task",
        {
            "task_name": task_name,
            "description": description,
            "when": when,
            "params": params,
        },
    ):
        return "Task scheduling is unavailable in this runtime."
    return f"Scheduled task '{task_name}' to run {when}: {description}"


def build_schedule_task_tool(owner: BaseTool) -> Callable:
    """Build the task-scheduling tool."""

    @tool
    def schedule_task(
        task_name: str,
        description: str,
        when: str,
        params: Optional[dict] = None,
    ) -> str:
        """Schedule a task to run automatically."""
        try:
            return _schedule_task_result(
                owner,
                task_name,
                description,
                when,
                params,
            )
        except Exception as exc:
            return _tool_error(owner, "scheduling task", exc)

    return schedule_task


def _validated_mode(mode: str) -> Optional[str]:
    """Return one validation error when the mode is unsupported."""
    valid_modes = ["autonomous", "supervised", "manual", "hybrid"]
    if mode in valid_modes:
        return None
    return f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}"


def _set_application_mode_result(
    owner: BaseTool,
    mode: str,
    reason: str,
    auto_approve: bool,
) -> str:
    """Set the autonomous-control mode when supported."""
    mode_error = _validated_mode(mode)
    if mode_error:
        return mode_error
    payload = {"mode": mode, "reason": reason}
    if auto_approve:
        payload["auto_approve"] = True
    if not owner.dispatch_tool_action("set_application_mode", payload):
        return "Application mode control is unavailable."
    suffix = " with auto-approval" if auto_approve else ""
    return f"Set application mode to '{mode}'{suffix}. Reason: {reason}"


def build_set_application_mode_tool(owner: BaseTool) -> Callable:
    """Build the application-mode control tool."""

    @tool
    def set_application_mode(
        mode: str,
        reason: str,
        auto_approve: bool = False,
    ) -> str:
        """Set the application's operational mode."""
        try:
            return _set_application_mode_result(
                owner,
                mode,
                reason,
                auto_approve,
            )
        except Exception as exc:
            return _tool_error(owner, "setting application mode", exc)

    return set_application_mode
