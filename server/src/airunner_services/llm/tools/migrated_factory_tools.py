"""Migrated factory tools — formerly in managers/tools/ mixins.

Each tool below was originally a closure-captured factory method on a
mixin class (ConversationTools, FileTools, SystemTools,
AutonomousControlTools, ImageTools).  They have been migrated to the
@tool() decorator system and receive the ToolManager instance via the
``agent`` parameter injected by ToolManager._wrap_tool_with_dependencies.
"""

from __future__ import annotations

import json
import os
from typing import Any

from airunner_services.llm.core.tool_registry import ToolCategory, tool

# ── File tools (from FileTools) ──────────────────────────────────────────────


@tool(
    name="list_files",
    category=ToolCategory.FILE,
    description="List files in a directory",
    return_direct=False,
    requires_agent=False,
)
def list_files(directory: str) -> str:
    """List files in a directory."""
    try:
        if not os.path.exists(directory):
            return f"Directory not found: {directory}"
        files = os.listdir(directory)
        return "\n".join(files) if files else "Directory is empty"
    except Exception as e:
        return f"Error listing files: {str(e)}"


# ── System / signal tools (from SystemTools) ────────────────────────────────


@tool(
    name="clear_conversation",
    category=ToolCategory.CONVERSATION,
    description="Clear the current conversation history",
    return_direct=True,
    requires_agent=True,
)
def clear_conversation(agent: Any = None) -> str:
    """Clear conversation history."""
    try:
        if (
            agent
            and agent.rag_manager
            and hasattr(agent.rag_manager, "clear_history")
        ):
            agent.rag_manager.clear_history({})
            return "Conversation history cleared"
        if agent and hasattr(agent, "dispatch_tool_action"):
            if agent.dispatch_tool_action("clear_conversation"):
                return "Conversation history cleared"
        return "Conversation history controls are unavailable."
    except Exception as e:
        return f"Error clearing conversation: {str(e)}"


@tool(
    name="emit_signal",
    category=ToolCategory.SYSTEM,
    description="Emit application signals to control UI and system",
    return_direct=False,
    requires_agent=True,
)
def emit_signal(
    signal_name: str,
    data: str = "{}",
    agent: Any = None,
) -> str:
    """Emit a signal to control the application."""
    try:
        try:
            data_dict = json.loads(data)
        except json.JSONDecodeError:
            return f"Error: data must be valid JSON. Got: {data}"
        if not signal_name:
            available = [
                "SD_GENERATE_IMAGE_SIGNAL",
                "CANVAS_CLEAR",
                "TOGGLE_TTS_SIGNAL",
                "TOGGLE_FULLSCREEN_SIGNAL",
                "LLM_CLEAR_HISTORY_SIGNAL",
                "QUIT_APPLICATION",
            ]
            return (
                f"Unknown signal '{signal_name}'. "
                f"Available: {', '.join(available)}"
            )
        if agent and hasattr(agent, "dispatch_tool_action"):
            if agent.dispatch_tool_action(
                "emit_signal",
                {"signal_name": signal_name, "data": data_dict},
            ):
                return f"Signal '{signal_name}' emitted successfully"
        return f"Unknown or unavailable signal '{signal_name}'."
    except Exception as e:
        return f"Error emitting signal: {str(e)}"
