"""Migrated factory tools — formerly in managers/tools/ mixins.

Each tool below was originally a closure-captured factory method on a
mixin class (ConversationTools, FileTools, SystemTools,
AutonomousControlTools, ImageTools).  They have been migrated to the
@tool() decorator system and receive the ToolManager instance via the
``agent`` parameter injected by ToolManager._wrap_tool_with_dependencies.
"""

from __future__ import annotations

from typing import Any

from airunner_services.llm.core.tool_registry import ToolCategory, tool

# ── File tools (from FileTools) ──────────────────────────────────────────────


@tool(
    name="log_agent_decision",
    category=ToolCategory.SYSTEM,
    description="Log an agent decision for audit trail",
    return_direct=True,
    requires_agent=True,
)
def log_agent_decision(
    decision: str,
    reasoning: str = "",
    agent: Any = None,
) -> str:
    """Log an agent decision."""
    try:
        import logging
        from datetime import datetime

        logger = logging.getLogger("airunner.agent.decisions")
        logger.info(
            "[%s] Decision: %s | Reasoning: %s",
            datetime.utcnow().isoformat(),
            decision,
            reasoning,
        )
        return "Decision logged"
    except Exception as e:
        return f"Error logging decision: {e}"


# ── Additional tools from SystemTools / ImageTools (fallback dispatch) ──────


@tool(
    name="toggle_tts",
    category=ToolCategory.SYSTEM,
    description="Enable or disable text-to-speech",
    return_direct=False,
    requires_agent=True,
)
def toggle_tts(enabled: bool, agent: Any = None) -> str:
    """Toggle text-to-speech."""
    try:
        if agent and hasattr(agent, "dispatch_tool_action"):
            if agent.dispatch_tool_action("toggle_tts", {"enabled": enabled}):
                return f"TTS {'enabled' if enabled else 'disabled'}"
        return "TTS controls are unavailable in this runtime."
    except Exception as e:
        return f"Error toggling TTS: {str(e)}"


@tool(
    name="update_mood",
    category=ToolCategory.MOOD,
    description="Update the chatbot emotional state",
    return_direct=False,
    requires_agent=True,
)
def update_mood(
    mood: str,
    emoji: str = "\U0001f610",
    agent: Any = None,
) -> str:
    """Update the chatbot's mood."""
    try:
        if agent and hasattr(agent, "dispatch_tool_action"):
            if agent.dispatch_tool_action(
                "bot_mood_updated",
                {"mood": mood, "emoji": emoji},
            ):
                return f"Mood updated to '{mood}' {emoji}"
        return "Mood updates are unavailable in this runtime."
    except Exception as e:
        return f"Error updating mood: {str(e)}"


@tool(
    name="generate_image",
    category=ToolCategory.IMAGE,
    description="Generate an image from a text prompt",
    return_direct=False,
    requires_agent=True,
)
def generate_image(
    prompt: str,
    negative_prompt: str = "",
    agent: Any = None,
) -> str:
    """Generate an image."""
    try:
        if agent and hasattr(agent, "dispatch_tool_action"):
            if agent.dispatch_tool_action(
                "generate_image",
                {"prompt": prompt, "negative_prompt": negative_prompt},
            ):
                return f"Generating image: {prompt}"
        return "Image generation is unavailable in this runtime."
    except Exception as e:
        return f"Error generating image: {str(e)}"


@tool(
    name="clear_canvas",
    category=ToolCategory.IMAGE,
    description="Clear the image canvas",
    return_direct=True,
    requires_agent=True,
)
def clear_canvas(agent: Any = None) -> str:
    """Clear the image canvas."""
    try:
        if agent and hasattr(agent, "dispatch_tool_action"):
            if agent.dispatch_tool_action("clear_canvas"):
                return "Canvas cleared"
        return "Canvas actions are unavailable in this runtime."
    except Exception as e:
        return f"Error clearing canvas: {str(e)}"


@tool(
    name="open_image",
    category=ToolCategory.IMAGE,
    description="Open an image from a file path",
    return_direct=False,
    requires_agent=True,
)
def open_image(file_path: str, agent: Any = None) -> str:
    """Open an image from file path."""
    try:
        import os as _os

        if not _os.path.exists(file_path):
            return f"File not found: {file_path}"
        if agent and hasattr(agent, "dispatch_tool_action"):
            if agent.dispatch_tool_action(
                "load_image_from_path", {"image_path": file_path}
            ):
                return f"Opened image: {file_path}"
        return "Image loading is unavailable in this runtime."
    except Exception as e:
        return f"Error opening image: {str(e)}"
