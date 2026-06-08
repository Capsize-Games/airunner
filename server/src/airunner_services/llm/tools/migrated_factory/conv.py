"""Migrated factory tools — formerly in managers/tools/ mixins.

Each tool below was originally a closure-captured factory method on a
mixin class (ConversationTools, FileTools, SystemTools,
AutonomousControlTools, ImageTools).  They have been migrated to the
@tool() decorator system and receive the ToolManager instance via the
``agent`` parameter injected by ToolManager._wrap_tool_with_dependencies.
"""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.llm.core.tool_registry import ToolCategory, tool

# ── File tools (from FileTools) ──────────────────────────────────────────────


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
