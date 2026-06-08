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
