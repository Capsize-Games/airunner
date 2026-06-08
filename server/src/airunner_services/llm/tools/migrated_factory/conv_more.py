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
