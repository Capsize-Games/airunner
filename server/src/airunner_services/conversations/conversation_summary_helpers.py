"""Extracted summary and loading helpers for conversation management."""

from __future__ import annotations

from typing import Any, Dict, List

from airunner_services.conversation_history_formatter import (
    load_formatted_conversation_history,
)
from airunner_services.llm.gpt_oss_parser import (
    has_gpt_oss_markup,
    parse_gpt_oss_response,
)
from airunner_services.llm.thinking_parser import (
    normalize_thinking_content,
    strip_stored_thinking_prefix,
)
from airunner_services.database.models.conversation import Conversation


def format_conversation_payload(
    conversation: Conversation,
    summary: str,
) -> Dict[str, Any]:
    """Serialize one conversation into JSON-safe metadata."""
    raw_messages = getattr(conversation, "value", None)
    if not isinstance(raw_messages, list):
        raw_messages = []

    return {
        "id": getattr(conversation, "id", None),
        "title": str(getattr(conversation, "title", "") or ""),
        "summary": summary,
        "current": bool(getattr(conversation, "current", False)),
        "timestamp": _serialize_timestamp(
            getattr(conversation, "timestamp", None)
        ),
        "chatbot_id": getattr(conversation, "chatbot_id", None),
        "chatbot_name": str(getattr(conversation, "chatbot_name", "") or ""),
        "user_id": getattr(conversation, "user_id", None),
        "user_name": str(getattr(conversation, "user_name", "") or ""),
        "message_count": len(raw_messages),
        "user_data": dict(getattr(conversation, "user_data", None) or {}),
    }


def _try_call_summarize(conversation: Conversation, logger: Any) -> str:
    """Call the conversation's summarize method if available."""
    summarize = getattr(conversation, "summarize", None)
    if not callable(summarize):
        return ""
    try:
        return str(summarize() or "").strip()
    except Exception as exc:
        logger.warning(
            "Failed to summarize conversation %s: %s",
            getattr(conversation, "id", None),
            exc,
        )
    return ""


def _persist_summary(
    conversation: Conversation, summary: str, logger: Any
) -> None:
    """Persist one conversation summary to the database."""
    try:
        Conversation.objects.update(conversation.id, summary=summary)
    except Exception as exc:
        logger.warning(
            "Failed to persist summary for conversation %s: %s",
            getattr(conversation, "id", None),
            exc,
        )


def resolve_conversation_summary(
    conversation: Conversation,
    logger: Any,
) -> str:
    """Return one cached or generated conversation summary."""
    summary = str(getattr(conversation, "summary", "") or "").strip()
    if summary:
        return summary

    summary = _try_call_summarize(conversation, logger)
    if summary:
        _persist_summary(conversation, summary, logger)
    return summary


def load_history(
    conversation: Conversation,
    logger: Any,
    max_messages: int = 50,
) -> List[Dict[str, Any]]:
    """Load and format one conversation history for display."""
    return load_formatted_conversation_history(
        logger=logger,
        conversation=conversation,
        max_messages=max_messages,
        normalize_thinking_content=normalize_thinking_content,
        strip_stored_thinking_prefix=strip_stored_thinking_prefix,
        has_gpt_oss_markup=has_gpt_oss_markup,
        parse_gpt_oss_response=parse_gpt_oss_response,
    )


def _serialize_timestamp(timestamp: Any) -> str:
    """Return one string representation for a conversation timestamp."""
    if timestamp is None:
        return ""
    formatter = getattr(timestamp, "isoformat", None)
    if callable(formatter):
        try:
            return formatter()
        except Exception:
            pass
    return str(timestamp)
