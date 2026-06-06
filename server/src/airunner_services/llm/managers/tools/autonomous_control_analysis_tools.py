"""Builders for autonomous-control analysis tools."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from langchain_core.tools import tool

from airunner_services.database.models.conversation import Conversation
from airunner_services.database.session import session_scope
from airunner_services.tools.base_tool import BaseTool


def _tool_error(owner: BaseTool, action: str, exc: Exception) -> str:
    """Log and format one analysis-tool error."""
    owner.logger.error("Error %s: %s", action, exc)
    return f"Error {action}: {exc}"


def _conversation_topics(conversations) -> list[tuple[str, int]]:
    """Return the top title keywords from one conversation collection."""
    topics: dict[str, int] = {}
    for conversation in conversations:
        for word in str(conversation.title or "").lower().split():
            if len(word) > 4:
                topics[word] = topics.get(word, 0) + 1
    return sorted(topics.items(), key=lambda item: item[1], reverse=True)[:5]


def _behavior_recommendations(
    avg_messages_per_conversation: float,
    total_conversations: int,
) -> list[str]:
    """Return recommendation lines for one behavior report."""
    if avg_messages_per_conversation < 5:
        lines = [
            "  - User prefers brief interactions - keep responses concise"
        ]
    else:
        lines = [
            "  - User engages in detailed discussions - provide thorough responses"
        ]
    if total_conversations > 20:
        lines.append("  - High activity user - consider proactive suggestions")
    return lines


def _behavior_report_lines(conversations, days_back: int) -> list[str]:
    """Build one user-behavior report from stored conversations."""
    total_conversations = len(conversations)
    total_messages = sum(
        len(item.value) if item.value else 0 for item in conversations
    )
    average = (
        total_messages / total_conversations if total_conversations else 0
    )
    lines = [
        f"User Behavior Analysis (last {days_back} days):",
        "\nActivity:",
        f"  - Total conversations: {total_conversations}",
        f"  - Total messages: {total_messages}",
        f"  - Avg messages/conversation: {average:.1f}",
        f"  - Conversations per day: {total_conversations / days_back:.1f}",
    ]
    for topic, count in _conversation_topics(conversations):
        if "\nTop Topics:" not in lines:
            lines.append("\nTop Topics:")
        lines.append(f"  - {topic}: {count} times")
    lines.append("\nRecommendations:")
    lines.extend(_behavior_recommendations(average, total_conversations))
    return lines


def _analyze_user_behavior_result(days_back: int) -> str:
    """Analyze recent conversation patterns for one behavior report."""
    with session_scope() as session:
        cutoff = datetime.now() - timedelta(days=days_back)
        conversations = (
            session.query(Conversation)
            .filter(Conversation.timestamp >= cutoff)
            .all()
        )
        if not conversations:
            return f"No conversation data found in the last {days_back} days."
        return "\n".join(_behavior_report_lines(conversations, days_back))


def build_analyze_user_behavior_tool(owner: BaseTool) -> Callable:
    """Build the user-behavior analysis tool."""

    @tool
    def analyze_user_behavior(days_back: int = 30) -> str:
        """Analyze recent user behavior."""
        try:
            return _analyze_user_behavior_result(days_back)
        except Exception as exc:
            return _tool_error(owner, "analyzing user behavior", exc)

    return analyze_user_behavior
