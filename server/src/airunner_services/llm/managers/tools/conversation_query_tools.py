"""Builders for conversation query tools."""

from __future__ import annotations

from typing import Callable, Optional

from langchain_core.tools import tool

from airunner_services.database.models.conversation import Conversation
from airunner_services.database.session import session_scope
from airunner_services.llm.managers.tools.conversation_tool_support import (
    conversation_details_text,
    conversation_list_text,
    conversation_search_matches,
    conversation_search_text,
    get_conversation,
    get_recent_conversations,
    get_target_conversation,
    handle_conversation_tool_error,
)
from airunner_services.tools.base_tool import BaseTool


def _list_conversations_result(
    limit: int,
    days_back: Optional[int],
) -> str:
    """Return the formatted recent-conversation list."""
    with session_scope() as session:
        conversations = get_recent_conversations(session, limit, days_back)
        return conversation_list_text(conversations)


def build_list_conversations_tool(owner: BaseTool) -> Callable:
    """Build the recent-conversation listing tool."""

    @tool
    def list_conversations(
        limit: int = 10,
        days_back: Optional[int] = None,
    ) -> str:
        """List recent conversations."""
        try:
            return _list_conversations_result(limit, days_back)
        except Exception as exc:
            return handle_conversation_tool_error(
                owner,
                "listing conversations",
                exc,
            )

    return list_conversations


def _get_conversation_result(
    conversation_id: int,
    include_messages: bool,
) -> str:
    """Return the formatted details for one conversation."""
    with session_scope() as session:
        conversation = get_conversation(session, conversation_id)
        if not conversation:
            return f"Conversation ID {conversation_id} not found."
        return conversation_details_text(conversation, include_messages)


def build_get_conversation_tool(owner: BaseTool) -> Callable:
    """Build the conversation detail tool."""

    @tool
    def get_conversation(
        conversation_id: int,
        include_messages: bool = True,
    ) -> str:
        """Get details for one conversation."""
        try:
            return _get_conversation_result(conversation_id, include_messages)
        except Exception as exc:
            return handle_conversation_tool_error(
                owner,
                "getting conversation",
                exc,
            )

    return get_conversation


def _persist_summary(conversation_id: int, summary: str) -> None:
    """Persist one generated conversation summary."""
    Conversation.objects.update(conversation_id, summary=summary)


def _summarize_conversation_result(
    conversation_id: Optional[int],
) -> str:
    """Return one stored or generated conversation summary."""
    with session_scope() as session:
        conversation = get_target_conversation(session, conversation_id)
        if not conversation:
            return "No conversation found to summarize."
        if conversation.summary:
            return f"Summary of Conversation {conversation.id}:\n{conversation.summary}"
        summary = conversation.summarize()
        target_id = conversation.id
    if not summary:
        return f"Conversation {target_id} has no messages to summarize."
    _persist_summary(target_id, summary)
    return f"Generated summary for Conversation {target_id}:\n{summary}"


def build_summarize_conversation_tool(owner: BaseTool) -> Callable:
    """Build the conversation summary tool."""

    @tool
    def summarize_conversation(
        conversation_id: Optional[int] = None,
    ) -> str:
        """Generate or return one conversation summary."""
        try:
            return _summarize_conversation_result(conversation_id)
        except Exception as exc:
            return handle_conversation_tool_error(
                owner,
                "summarizing conversation",
                exc,
            )

    return summarize_conversation


def _search_conversations_result(
    query: str,
    limit: int,
    search_messages: bool,
) -> str:
    """Return the formatted search results for one query."""
    with session_scope() as session:
        conversations = (
            session.query(Conversation).order_by(Conversation.id.desc()).all()
        )
        matches = conversation_search_matches(
            conversations,
            query,
            limit,
            search_messages,
        )
        return conversation_search_text(matches, query)


def build_search_conversations_tool(owner: BaseTool) -> Callable:
    """Build the conversation search tool."""

    @tool
    def search_conversations(
        query: str,
        limit: int = 10,
        search_messages: bool = True,
    ) -> str:
        """Search stored conversations."""
        try:
            return _search_conversations_result(
                query,
                limit,
                search_messages,
            )
        except Exception as exc:
            return handle_conversation_tool_error(
                owner,
                "searching conversations",
                exc,
            )

    return search_conversations
