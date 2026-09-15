"""Conversation DTO used by GUI persistence clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ConversationRecord:
    """Plain conversation data transferred from daemon API responses."""

    id: Optional[int] = None
    title: str = ""
    summary: str = ""
    current: bool = False
    timestamp: str = ""
    chatbot_id: Optional[int] = None
    chatbot_name: str = ""
    user_id: Optional[int] = None
    user_name: str = ""
    message_count: int = 0
    user_data: Dict[str, Any] = field(default_factory=dict)
    value: list[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_payload(
        cls,
        payload: Optional[Dict[str, Any]],
        *,
        messages: Optional[list[Dict[str, Any]]] = None,
    ) -> "ConversationRecord":
        """Build one DTO from a daemon response payload."""
        data = dict(payload or {})
        value = list(messages or [])
        message_count = int(data.get("message_count") or len(value))
        return cls(
            id=data.get("id"),
            title=str(data.get("title", "") or ""),
            summary=str(data.get("summary", "") or ""),
            current=bool(data.get("current", False)),
            timestamp=str(data.get("timestamp", "") or ""),
            chatbot_id=data.get("chatbot_id"),
            chatbot_name=str(data.get("chatbot_name", "") or ""),
            user_id=data.get("user_id"),
            user_name=str(data.get("user_name", "") or ""),
            message_count=message_count,
            user_data=dict(data.get("user_data") or {}),
            value=value,
        )