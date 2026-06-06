"""Builders for conversation mutation tools."""

from __future__ import annotations

from typing import Callable, Optional

from langchain_core.tools import tool

from airunner_services.database.models.conversation import Conversation
from airunner_services.database.session import session_scope
from airunner_services.llm.managers.tools.conversation_tool_support import (
    conversation_message_count,
    conversation_title,
    get_conversation,
    get_target_conversation,
    handle_conversation_tool_error,
)
from airunner_services.tools.base_tool import BaseTool


def _update_conversation_title_result(
    owner: BaseTool,
    title: str,
    conversation_id: Optional[int],
) -> str:
    """Persist one conversation title update and notify listeners."""
    with session_scope() as session:
        conversation = get_target_conversation(session, conversation_id)
        if not conversation:
            return "No conversation found to update."
        old_title = conversation_title(conversation)
        session.query(Conversation).filter_by(id=conversation.id).update(
            {"title": title}
        )
        owner.dispatch_tool_action(
            "conversation_title_updated",
            {"conversation_id": conversation.id, "title": title},
        )
        return (
            f"Updated conversation {conversation.id} title: "
            f"'{old_title}' → '{title}'"
        )


def build_update_conversation_title_tool(owner: BaseTool) -> Callable:
    """Build the conversation title update tool."""

    @tool
    def update_conversation_title(
        title: str,
        conversation_id: Optional[int] = None,
    ) -> str:
        """Set or update a conversation title."""
        try:
            return _update_conversation_title_result(
                owner,
                title,
                conversation_id,
            )
        except Exception as exc:
            return handle_conversation_tool_error(
                owner,
                "updating conversation title",
                exc,
            )

    return update_conversation_title


def _switch_conversation_result(
    owner: BaseTool,
    conversation_id: int,
) -> str:
    """Switch the active conversation and notify the UI."""
    with session_scope() as session:
        conversation = get_conversation(session, conversation_id)
        if not conversation:
            return f"Conversation ID {conversation_id} not found."
        session.query(Conversation).update({"current": False})
        session.query(Conversation).filter_by(id=conversation_id).update(
            {"current": True}
        )
        owner.dispatch_tool_action(
            "load_conversation",
            {"conversation_id": conversation_id},
        )
        title = conversation_title(conversation)
        count = conversation_message_count(conversation)
        return (
            f"Switched to conversation {conversation_id}: "
            f"'{title}' ({count} messages)"
        )


def build_switch_conversation_tool(owner: BaseTool) -> Callable:
    """Build the active-conversation switch tool."""

    @tool
    def switch_conversation(conversation_id: int) -> str:
        """Switch to a different conversation."""
        try:
            return _switch_conversation_result(owner, conversation_id)
        except Exception as exc:
            return handle_conversation_tool_error(
                owner,
                "switching conversation",
                exc,
            )

    return switch_conversation


def _create_new_conversation_result(
    owner: BaseTool,
    title: Optional[str],
) -> str:
    """Create one new conversation and optionally set its title."""
    conversation = Conversation.create()
    if not conversation:
        return "Failed to create new conversation."
    if title:
        Conversation.objects.update(conversation.id, title=title)
    owner.dispatch_tool_action(
        "new_conversation",
        {"conversation_id": conversation.id},
    )
    title_suffix = f" with title '{title}'" if title else ""
    return f"Created new conversation {conversation.id}{title_suffix}"


def build_create_new_conversation_tool(owner: BaseTool) -> Callable:
    """Build the new-conversation creation tool."""

    @tool
    def create_new_conversation(title: Optional[str] = None) -> str:
        """Create a new conversation."""
        try:
            return _create_new_conversation_result(owner, title)
        except Exception as exc:
            return handle_conversation_tool_error(
                owner,
                "creating conversation",
                exc,
            )

    return create_new_conversation


def _delete_conversation_result(
    owner: BaseTool,
    conversation_id: int,
    confirm: bool,
) -> str:
    """Delete one non-current conversation after confirmation."""
    if not confirm:
        return (
            f"WARNING: This will permanently delete conversation "
            f"{conversation_id}. Call again with confirm=True to proceed."
        )
    with session_scope() as session:
        conversation = get_conversation(session, conversation_id)
        if not conversation:
            return f"Conversation ID {conversation_id} not found."
        if conversation.current:
            return (
                "Cannot delete the current active conversation. "
                "Switch to another first."
            )
        title = conversation_title(conversation)
        Conversation.delete(pk=conversation_id)
        owner.dispatch_tool_action(
            "conversation_deleted",
            {"conversation_id": conversation_id},
        )
        return f"Deleted conversation {conversation_id}: '{title}'"


def build_delete_conversation_tool(owner: BaseTool) -> Callable:
    """Build the conversation deletion tool."""

    @tool
    def delete_conversation(
        conversation_id: int,
        confirm: bool = False,
    ) -> str:
        """Delete a conversation permanently."""
        try:
            return _delete_conversation_result(
                owner,
                conversation_id,
                confirm,
            )
        except Exception as exc:
            return handle_conversation_tool_error(
                owner,
                "deleting conversation",
                exc,
            )

    return delete_conversation
