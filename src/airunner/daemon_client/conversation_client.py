"""Typed daemon client for GUI conversation persistence flows."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlencode

from airunner.daemon_client.gui_daemon_client import GuiDaemonClient


class ConversationDaemonClient:
    """Typed client for daemon-backed conversation endpoints."""

    def __init__(self, daemon_client: GuiDaemonClient) -> None:
        """Store the shared GUI daemon client."""
        self._client = daemon_client

    def list_conversations(self, *, limit: int = 50) -> list[Dict[str, Any]]:
        """Return the serialized conversation list payload."""
        response = self._client._request(
            "GET",
            f"/api/v1/conversations?{urlencode({'limit': limit})}",
        )
        return response.json().get("conversations", [])

    def get_conversation_session(
        self,
        *,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
    ) -> Dict[str, Any]:
        """Return one serialized conversation session payload."""
        query: Dict[str, Any] = {"max_messages": max_messages}
        if conversation_id is not None:
            query["conversation_id"] = conversation_id
        response = self._client._request(
            "GET",
            f"/api/v1/conversations/session?{urlencode(query)}",
        )
        return response.json()

    def select_conversation(
        self,
        *,
        conversation_id: int,
        max_messages: int = 50,
    ) -> Dict[str, Any]:
        """Mark one conversation current and return its session payload."""
        response = self._client._request(
            "POST",
            "/api/v1/conversations/select",
            json_payload={
                "conversation_id": conversation_id,
                "max_messages": max_messages,
            },
        )
        return response.json()

    def create_conversation(
        self,
        *,
        max_messages: int = 50,
    ) -> Dict[str, Any]:
        """Create one new current conversation through the daemon."""
        response = self._client._request(
            "POST",
            "/api/v1/conversations",
            json_payload={"max_messages": max_messages},
        )
        return response.json()

    def delete_conversation(self, conversation_id: int) -> Dict[str, Any]:
        """Delete one conversation through the daemon."""
        response = self._client._request(
            "DELETE",
            f"/api/v1/conversations/{conversation_id}",
        )
        return response.json()

    def delete_all_conversations(self) -> Dict[str, Any]:
        """Delete all conversations through the daemon in tests only."""
        response = self._client._request(
            "DELETE",
            "/api/v1/conversations",
        )
        return response.json()

    def update_conversation_messages(
        self,
        conversation_id: int,
        messages: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Replace one conversation's stored messages through the daemon."""
        response = self._client._request(
            "PUT",
            f"/api/v1/conversations/{conversation_id}/messages",
            json_payload={"messages": list(messages)},
        )
        return response.json()

    def update_conversation_user_data(
        self,
        conversation_id: int,
        user_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Replace one conversation's stored user-data through the daemon."""
        response = self._client._request(
            "PUT",
            f"/api/v1/conversations/{conversation_id}/user-data",
            json_payload={"user_data": dict(user_data or {})},
        )
        return response.json()