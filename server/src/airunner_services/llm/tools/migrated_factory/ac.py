"""Migrated factory tools — formerly in managers/tools/ mixins.

Each tool below was originally a closure-captured factory method on a
mixin class (ConversationTools, FileTools, SystemTools,
AutonomousControlTools, ImageTools).  They have been migrated to the
@tool() decorator system and receive the ToolManager instance via the
``agent`` parameter injected by ToolManager._wrap_tool_with_dependencies.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from airunner_services.llm.core.tool_registry import ToolCategory, tool

# ── File tools (from FileTools) ──────────────────────────────────────────────


@tool(
    name="get_application_state",
    category=ToolCategory.SYSTEM,
    description="Get current application state and capabilities",
    return_direct=False,
    requires_agent=True,
)
def get_application_state(agent: Any = None) -> str:
    """Return the current application state."""
    try:
        state = {
            "application": {
                "name": "AI Runner",
                "version": "2.0",
                "mode": "autonomous",
            },
            "llm": {
                "active": True,
                "model": (
                    getattr(agent, "active_llm_model_name", "unknown")
                    if agent
                    else "unknown"
                ),
                "tools_count": (
                    len(agent.get_all_tools())
                    if agent and hasattr(agent, "get_all_tools")
                    else 0
                ),
            },
            "conversation": {
                "current_id": (
                    getattr(agent, "current_conversation_id", None)
                    if agent
                    else None
                ),
                "has_context": True,
            },
            "capabilities": {
                "image_generation": True,
                "rag": agent.rag_manager is not None if agent else False,
                "knowledge_base": True,
                "web_access": True,
                "code_execution": True,
            },
        }
        return json.dumps(state, indent=2)
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="schedule_task",
    category=ToolCategory.SYSTEM,
    description="Schedule a task to run automatically",
    return_direct=False,
    requires_agent=True,
)
def schedule_task(
    task_name: str,
    description: str,
    when: str,
    params: Optional[str] = None,
    agent: Any = None,
) -> str:
    """Schedule a task."""
    try:
        params_dict = json.loads(params) if params else None
        if not _ac_dispatch(
            agent,
            "schedule_task",
            {
                "task_name": task_name,
                "description": description,
                "when": when,
                "params": params_dict,
            },
        ):
            return "Task scheduling is unavailable."
        return f"Scheduled task '{task_name}' to run {when}: {description}"
    except Exception as e:
        return f"Error scheduling task: {e}"


@tool(
    name="set_application_mode",
    category=ToolCategory.SYSTEM,
    description="Switch the application mode",
    return_direct=True,
    requires_agent=True,
)
def set_application_mode(mode: str, agent: Any = None) -> str:
    """Set the application mode."""
    try:
        if not _ac_dispatch(agent, "set_application_mode", {"mode": mode}):
            return "Mode switching is unavailable."
        return f"Application mode set to '{mode}'"
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="request_user_input",
    category=ToolCategory.SYSTEM,
    description="Request input from the user via UI",
    return_direct=True,
    requires_agent=True,
)
def request_user_input(
    prompt: str,
    input_type: str = "text",
    agent: Any = None,
) -> str:
    """Request user input via UI."""
    try:
        if not _ac_dispatch(
            agent,
            "request_user_input",
            {"prompt": prompt, "input_type": input_type},
        ):
            return "User input requests are unavailable."
        return f"User input requested: {prompt}"
    except Exception as e:
        return f"Error: {e}"
