"""Shared helpers for conversation-management tools."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from airunner_services.database.models.conversation import Conversation
from airunner_services.tools.base_tool import BaseTool

NO_TITLE = "(no title)"


def conversation_title(conversation: Conversation) -> str:
    """Return one conversation title with a stable fallback."""
    return conversation.title or NO_TITLE


def conversation_message_count(conversation: Conversation) -> int:
    """Return the number of stored messages for one conversation."""
    return len(conversation.value) if conversation.value else 0


def get_recent_conversations(
    session,
    limit: int,
    days_back: Optional[int],
):
    """Return recent conversations ordered newest-first."""
    query = session.query(Conversation).order_by(Conversation.id.desc())
    if days_back:
        cutoff = datetime.now() - timedelta(days=days_back)
        query = query.filter(Conversation.timestamp >= cutoff)
    return query.limit(limit).all()


def get_conversation(session, conversation_id: int) -> Optional[Conversation]:
    """Return one conversation by database id."""
    return session.query(Conversation).filter_by(id=conversation_id).first()


def get_current_conversation(session) -> Optional[Conversation]:
    """Return the current active conversation when present."""
    return session.query(Conversation).filter_by(current=True).first()


def get_target_conversation(
    session,
    conversation_id: Optional[int],
) -> Optional[Conversation]:
    """Return the requested conversation or the current one."""
    if conversation_id:
        return get_conversation(session, conversation_id)
    return get_current_conversation(session)


def conversation_list_line(conversation: Conversation) -> str:
    """Format one list row for a conversation."""
    timestamp = conversation.timestamp.strftime("%Y-%m-%d %H:%M")
    current = " [CURRENT]" if conversation.current else ""
    message_count = conversation_message_count(conversation)
    return (
        f"ID {conversation.id}: {conversation_title(conversation)} - "
        f"{timestamp} ({message_count} messages){current}"
    )


def conversation_list_text(conversations) -> str:
    """Format a recent-conversation query response."""
    if not conversations:
        return "No conversations found."
    lines = [f"Found {len(conversations)} conversation(s):\n"]
    lines.extend(
        conversation_list_line(conversation) for conversation in conversations
    )
    return "\n".join(lines)


def conversation_detail_lines(conversation: Conversation) -> list[str]:
    """Return the fixed detail lines for one conversation."""
    timestamp = conversation.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    participants = f"{conversation.user_name} ↔ {conversation.chatbot_name}"
    status = "CURRENT" if conversation.current else "archived"
    return [
        f"Conversation ID: {conversation.id}",
        f"Title: {conversation_title(conversation)}",
        f"Created: {timestamp}",
        f"Participants: {participants}",
        f"Messages: {conversation_message_count(conversation)}",
        f"Status: {status}",
    ]


def conversation_message_line(index: int, message: dict) -> str:
    """Format one stored message preview line."""
    role = message.get("name", message.get("role", "unknown"))
    content = str(message.get("content", ""))
    preview = f"{content[:100]}..." if len(content) > 100 else content
    timestamp = message.get("timestamp", "")
    return f"{index}. [{timestamp}] {role}: {preview}"


def conversation_message_lines(conversation: Conversation) -> list[str]:
    """Return preview lines for the last stored conversation messages."""
    messages = list(conversation.value or [])[-20:]
    if not messages:
        return []
    lines = ["\n--- Messages ---"]
    lines.extend(
        conversation_message_line(index, message)
        for index, message in enumerate(messages, 1)
    )
    return lines


def conversation_details_text(
    conversation: Conversation,
    include_messages: bool,
) -> str:
    """Format one conversation detail response."""
    lines = conversation_detail_lines(conversation)
    if conversation.summary:
        lines.append(f"\nSummary: {conversation.summary}")
    if include_messages:
        lines.extend(conversation_message_lines(conversation))
    return "\n".join(lines)


def conversation_search_score(
    conversation: Conversation,
    query_lower: str,
    search_messages: bool,
) -> int:
    """Return one simple relevance score for a conversation search."""
    score = 0
    if conversation.title and query_lower in conversation.title.lower():
        score += 10
    if conversation.summary and query_lower in conversation.summary.lower():
        score += 5
    if search_messages and conversation.value:
        score += sum(
            1
            for message in conversation.value
            if query_lower in str(message.get("content", "")).lower()
        )
    return score


def conversation_search_matches(
    conversations,
    query: str,
    limit: int,
    search_messages: bool,
):
    """Return sorted search matches for one conversation query."""
    query_lower = query.lower()
    matches = []
    for conversation in conversations:
        score = conversation_search_score(
            conversation,
            query_lower,
            search_messages,
        )
        if score > 0:
            matches.append((score, conversation))
    matches.sort(reverse=True, key=lambda item: item[0])
    return matches[:limit]


def conversation_search_line(score: int, conversation: Conversation) -> str:
    """Format one conversation search result line."""
    timestamp = conversation.timestamp.strftime("%Y-%m-%d")
    message_count = conversation_message_count(conversation)
    return (
        f"ID {conversation.id} [score: {score}]: "
        f"{conversation_title(conversation)} - {timestamp} "
        f"({message_count} msgs)"
    )


def conversation_search_text(matches, query: str) -> str:
    """Format the final search response for conversation matches."""
    if not matches:
        return f"No conversations found matching '{query}'"
    lines = [f"Found {len(matches)} conversation(s) matching '{query}':\n"]
    lines.extend(
        conversation_search_line(score, conversation)
        for score, conversation in matches
    )
    return "\n".join(lines)


def handle_conversation_tool_error(
    owner: BaseTool,
    action: str,
    exc: Exception,
) -> str:
    """Log and format one conversation-tool error response."""
    owner.logger.error("Error %s: %s", action, exc)
    return f"Error {action}: {exc}"
