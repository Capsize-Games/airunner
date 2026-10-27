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
from typing import Any, Optional

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


# ── Conversation tools (from ConversationTools) ────────────────────────────


def _conv_details_text(conv: Any) -> str:
    """Return a human-readable summary of one conversation record."""
    title = getattr(conv, "title", "") or "Untitled"
    return f'Conversation {conv.id}: "{title}"'


def _safe_session_scope():
    """Return a session-scope context manager."""
    from airunner_services.database import session_scope

    return session_scope  # type: ignore[return-value]


@tool(
    name="list_conversations",
    category=ToolCategory.CONVERSATION,
    description="List recent conversations",
    return_direct=False,
    requires_agent=False,
)
def list_conversations(
    limit: int = 10,
    days_back: Optional[int] = None,
) -> str:
    """List recent conversations."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )
        from datetime import datetime, timedelta

        with _safe_session_scope()() as session:  # type: ignore[misc]
            query = session.query(Conversation)
            if days_back:
                cutoff = datetime.utcnow() - timedelta(days=days_back)
                query = query.filter(Conversation.updated_at >= cutoff)
            conversations = (
                query.order_by(Conversation.updated_at.desc())
                .limit(limit)
                .all()
            )
            if not conversations:
                return "No conversations found."
            lines = [
                f"{conv.id}: {_conv_details_text(conv)}"
                for conv in conversations
            ]
            return "\n".join(lines)
    except Exception as e:
        return f"Error listing conversations: {e}"


@tool(
    name="get_conversation",
    category=ToolCategory.CONVERSATION,
    description="Get conversation details by ID",
    return_direct=False,
    requires_agent=False,
)
def get_conversation(conversation_id: int) -> str:
    """Get a specific conversation."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        with _safe_session_scope()() as session:
            conv = session.query(Conversation).get(conversation_id)
            if not conv:
                return f"Conversation {conversation_id} not found."
            messages = getattr(conv, "value", []) or []
            lines = [f'Conversation {conv.id}: "{conv.title}"']
            for m in messages[-20:]:
                role = m.get("role", "unknown")
                content = m.get("content", "")[:200]
                lines.append(f"  [{role}] {content}")
            return "\n".join(lines)
    except Exception as e:
        return f"Error getting conversation: {e}"


@tool(
    name="summarize_conversation",
    category=ToolCategory.CONVERSATION,
    description="Summarize a conversation by ID",
    return_direct=False,
    requires_agent=False,
)
def summarize_conversation(
    conversation_id: Optional[int] = None,
) -> str:
    """Summarize a conversation."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        with _safe_session_scope()() as session:
            conv = (
                session.query(Conversation)
                .order_by(Conversation.id.desc())
                .first()
                if conversation_id is None
                else session.query(Conversation).get(conversation_id)
            )
            if not conv:
                return "No conversation found to summarize."
            if hasattr(conv, "summary") and conv.summary:
                return f"Summary of Conversation {conv.id}:\n{conv.summary}"
            if hasattr(conv, "summarize"):
                summary = conv.summarize()
                if summary:
                    return (
                        f"Generated summary for Conversation {conv.id}:"
                        f"\n{summary}"
                    )
            return f"Conversation {conv.id} has no messages to summarize."
    except Exception as e:
        return f"Error summarizing conversation: {e}"


@tool(
    name="update_conversation_title",
    category=ToolCategory.CONVERSATION,
    description="Update a conversation title",
    return_direct=True,
    requires_agent=True,
)
def update_conversation_title(
    conversation_id: int,
    title: str,
    agent: Any = None,
) -> str:
    """Update a conversation's title."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        with _safe_session_scope()() as session:
            conv = session.query(Conversation).get(conversation_id)
            if not conv:
                return f"Conversation {conversation_id} not found."
            conv.title = title
            session.commit()
        if agent and hasattr(agent, "dispatch_tool_action"):
            agent.dispatch_tool_action(
                "conversation_updated",
                {"conversation_id": conversation_id, "title": title},
            )
        return f'Conversation {conversation_id} title updated to "{title}"'
    except Exception as e:
        return f"Error updating title: {e}"


@tool(
    name="switch_conversation",
    category=ToolCategory.CONVERSATION,
    description="Switch to a different conversation",
    return_direct=True,
    requires_agent=True,
)
def switch_conversation(
    conversation_id: int,
    agent: Any = None,
) -> str:
    """Switch the active conversation."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        with _safe_session_scope()() as session:
            conv = session.query(Conversation).get(conversation_id)
            if not conv:
                return f"Conversation {conversation_id} not found."
        if agent and hasattr(agent, "dispatch_tool_action"):
            agent.dispatch_tool_action(
                "switch_conversation",
                {"conversation_id": conversation_id},
            )
        return f"Switched to conversation {conversation_id}"
    except Exception as e:
        return f"Error switching conversation: {e}"


@tool(
    name="create_new_conversation",
    category=ToolCategory.CONVERSATION,
    description="Create a new conversation",
    return_direct=True,
    requires_agent=True,
)
def create_new_conversation(
    title: str = "",
    agent: Any = None,
) -> str:
    """Create a new conversation."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        with _safe_session_scope()() as session:
            conv = Conversation()
            if title:
                conv.title = title  # type: ignore[assignment]
            session.add(conv)
            session.commit()
            conv_id = conv.id
        if agent and hasattr(agent, "dispatch_tool_action"):
            agent.dispatch_tool_action(
                "new_conversation",
                {"conversation_id": conv_id},
            )
        return f"Created new conversation {conv_id}"
    except Exception as e:
        return f"Error creating conversation: {e}"


@tool(
    name="search_conversations",
    category=ToolCategory.CONVERSATION,
    description="Search conversations by keyword",
    return_direct=False,
    requires_agent=False,
)
def search_conversations(query: str) -> str:
    """Search conversations for a keyword."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        with _safe_session_scope()() as session:
            convs = (
                session.query(Conversation)
                .filter(Conversation.title.ilike(f"%{query}%"))
                .limit(10)
                .all()
            )
            if not convs:
                return f'No conversations matching "{query}".'
            lines = [f"{c.id}: {_conv_details_text(c)}" for c in convs]
            return "\n".join(lines)
    except Exception as e:
        return f"Error searching conversations: {e}"


@tool(
    name="delete_conversation",
    category=ToolCategory.CONVERSATION,
    description="Delete a conversation by ID",
    return_direct=True,
    requires_agent=True,
)
def delete_conversation(
    conversation_id: int,
    agent: Any = None,
) -> str:
    """Delete a conversation."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        with _safe_session_scope()() as session:
            conv = session.query(Conversation).get(conversation_id)
            if not conv:
                return f"Conversation {conversation_id} not found."
            session.delete(conv)
            session.commit()
        if agent and hasattr(agent, "dispatch_tool_action"):
            agent.dispatch_tool_action(
                "conversation_deleted",
                {"conversation_id": conversation_id},
            )
        return f"Deleted conversation {conversation_id}"
    except Exception as e:
        return f"Error deleting conversation: {e}"


# ── Autonomous control tools (from AutonomousControlTools) ───────────────────


def _ac_dispatch(agent: Any, action: str, payload: dict) -> bool:
    """Dispatch one autonomous-control action."""
    if agent and hasattr(agent, "dispatch_tool_action"):
        return agent.dispatch_tool_action(action, payload)
    return False


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


@tool(
    name="analyze_user_behavior",
    category=ToolCategory.ANALYSIS,
    description="Analyze user interaction patterns",
    return_direct=False,
    requires_agent=True,
)
def analyze_user_behavior(agent: Any = None) -> str:
    """Analyze user behavior patterns."""
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        with _safe_session_scope()() as session:
            convs = (
                session.query(Conversation)
                .order_by(Conversation.updated_at.desc())
                .limit(10)
                .all()
            )
            total_msgs = sum(len(getattr(c, "value", []) or []) for c in convs)
        return (
            f"Recent activity: {len(convs)} conversations, "
            f"{total_msgs} total messages."
        )
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="propose_action",
    category=ToolCategory.ANALYSIS,
    description="Propose an autonomous action for user approval",
    return_direct=False,
    requires_agent=True,
)
def propose_action(
    action_description: str,
    agent: Any = None,
) -> str:
    """Propose an autonomous action."""
    try:
        if not _ac_dispatch(
            agent,
            "propose_action",
            {"description": action_description},
        ):
            return "Action proposals are unavailable."
        return f"Action proposed: {action_description}"
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="monitor_system_health",
    category=ToolCategory.SYSTEM,
    description="Check system health metrics",
    return_direct=False,
    requires_agent=True,
)
def monitor_system_health(agent: Any = None) -> str:
    """Monitor system health."""
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        return (
            f"System health: CPU {cpu}%, "
            f"Memory {mem.percent}% ({mem.available // 1024 // 1024} MB free)"
        )
    except ImportError:
        return "System health monitoring unavailable (psutil not installed)."
    except Exception as e:
        return f"Error: {e}"


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
