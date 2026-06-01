"""Daemon-backed conversation loader for GUI persistence flows."""

from typing import Any, Dict, List, Optional

from airunner.components.conversations.conversation_record import (
    ConversationRecord,
)
from airunner.daemon_client.conversation_client import (
    ConversationDaemonClient,
)
from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ConversationHistoryManager:
    """Handles GUI-side conversation loading through typed daemon clients."""

    def __init__(
        self,
        daemon_client: Optional[GuiDaemonClient] = None,
    ) -> None:
        """Initialize one daemon-backed conversation history manager."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        client = daemon_client or GuiDaemonClient()
        self._client = ConversationDaemonClient(client)

    def get_current_conversation(self) -> Optional[ConversationRecord]:
        """Return the current daemon-side conversation if one exists."""
        for conversation in self.list_conversations(limit=0):
            if conversation.current:
                return conversation
        self.logger.info("No current conversation found.")
        return None

    def get_most_recent_conversation_id(self) -> Optional[int]:
        """Return the most recent conversation ID if one exists."""
        conversations = self.list_conversations(limit=1)
        if not conversations:
            self.logger.info("No conversations found.")
            return None
        conversation_id = conversations[0].id
        self.logger.info("Most recent conversation ID: %s", conversation_id)
        return conversation_id

    def list_conversations(
        self,
        limit: int = 50,
    ) -> List[ConversationRecord]:
        """Return serialized conversation summaries from the daemon."""
        try:
            payload = self._client.list_conversations(limit=limit)
        except RuntimeError as exc:
            self._log_client_failure("list conversations", exc)
            return []
        return [ConversationRecord.from_payload(item) for item in payload]

    def get_conversation_session(
        self,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
        mark_current: bool = False,
    ) -> Dict[str, Any]:
        """Return one daemon-backed conversation record plus messages."""
        try:
            payload = self._load_session_payload(
                conversation_id=conversation_id,
                max_messages=max_messages,
                mark_current=mark_current,
            )
        except RuntimeError as exc:
            self._log_client_failure("load conversation session", exc)
            return self._empty_session()
        return self._session_response(payload)

    def create_conversation(
        self,
        max_messages: int = 50,
    ) -> Optional[ConversationRecord]:
        """Create one new daemon-backed conversation and return its DTO."""
        try:
            payload = self._client.create_conversation(
                max_messages=max_messages,
            )
        except RuntimeError as exc:
            self._log_client_failure("create conversation", exc)
            return None
        return self._session_response(payload).get("conversation")

    def select_conversation(
        self,
        conversation_id: int,
        max_messages: int = 50,
    ) -> Dict[str, Any]:
        """Mark one daemon-backed conversation current."""
        return self.get_conversation_session(
            conversation_id=conversation_id,
            max_messages=max_messages,
            mark_current=True,
        )

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete one conversation through the daemon API."""
        try:
            payload = self._client.delete_conversation(conversation_id)
        except RuntimeError as exc:
            self._log_client_failure("delete conversation", exc)
            return False
        return bool(payload.get("deleted"))

    def delete_all_conversations(self) -> int:
        """Delete all conversations through the daemon API in tests only."""
        try:
            payload = self._client.delete_all_conversations()
        except RuntimeError as exc:
            self._log_client_failure("delete all conversations", exc)
            return 0
        return int(payload.get("deleted") or 0)

    def update_conversation_messages(
        self,
        conversation_id: int,
        messages: List[Dict[str, Any]],
    ) -> bool:
        """Persist one conversation message list through the daemon API."""
        try:
            payload = self._client.update_conversation_messages(
                conversation_id,
                messages,
            )
        except RuntimeError as exc:
            self._log_client_failure("update conversation messages", exc)
            return False
        return bool(payload.get("updated"))

    def update_conversation_user_data(
        self,
        conversation_id: int,
        user_data: Dict[str, Any],
    ) -> bool:
        """Persist one conversation user-data payload through the daemon API."""
        try:
            payload = self._client.update_conversation_user_data(
                conversation_id,
                user_data,
            )
        except RuntimeError as exc:
            self._log_client_failure("update conversation user data", exc)
            return False
        return bool(payload.get("updated"))

    def load_conversation_history(
        self,
        conversation: Optional[ConversationRecord] = None,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
    ) -> List[Dict[str, Any]]:
        """Load one formatted conversation history through the daemon API."""
        if conversation is not None and conversation_id is None:
            messages = list(getattr(conversation, "value", []) or [])
            return messages[-max_messages:]
        session = self.get_conversation_session(
            conversation_id=conversation_id,
            max_messages=max_messages,
        )
        return session.get("messages", [])

    def _load_session_payload(
        self,
        *,
        conversation_id: Optional[int],
        max_messages: int,
        mark_current: bool,
    ) -> Dict[str, Any]:
        """Fetch one raw session payload from the daemon conversation API."""
        if mark_current and conversation_id is not None:
            return self._client.select_conversation(
                conversation_id=conversation_id,
                max_messages=max_messages,
            )
        return self._client.get_conversation_session(
            conversation_id=conversation_id,
            max_messages=max_messages,
        )

    @staticmethod
    def _empty_session() -> Dict[str, Any]:
        """Return one empty conversation-session payload."""
        return {
            "conversation": None,
            "conversation_id": None,
            "messages": [],
        }

    def _session_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert one daemon session payload into GUI DTO form."""
        messages = list(payload.get("messages") or [])
        conversation_payload = payload.get("conversation")
        if not isinstance(conversation_payload, dict):
            return self._empty_session()
        conversation = ConversationRecord.from_payload(
            conversation_payload,
            messages=messages,
        )
        return {
            "conversation": conversation,
            "conversation_id": conversation.id,
            "messages": messages,
        }

    def _log_client_failure(self, action: str, exc: Exception) -> None:
        """Log one daemon-client failure for GUI persistence operations."""
        self.logger.warning(
            "Failed to %s via daemon client: %s",
            action,
            exc,
        )
