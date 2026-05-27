"""Service-owned conversation history loader and formatter."""

from typing import Any, Dict, List, Optional

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
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.database.models.conversation import Conversation


class ConversationHistoryManager:
    """Handles fetching and formatting of conversation history."""

    def __init__(self) -> None:
        """Initialize one conversation history manager."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def get_current_conversation(self) -> Optional[Conversation]:
        """Fetch the current conversation if one exists."""
        conversations = Conversation.objects.filter_by(current=True)
        if len(conversations) == 0:
            self.logger.info("No current conversation found.")
            return None
        self.logger.debug("Fetching the current conversation.")
        try:
            conversation = conversations[0]
            if conversation:
                self.logger.debug(
                    f"Current conversation ID: {conversation.id}"
                )
                return conversation
            self.logger.info("No current conversation found.")
            return None
        except Exception as exc:
            self.logger.error(
                f"Error fetching current conversation: {exc}",
                exc_info=True,
            )
            return None

    def get_most_recent_conversation_id(self) -> Optional[int]:
        """Fetch the most recent conversation id if one exists."""
        self.logger.debug("Fetching the most recent conversation ID.")
        try:
            conversation = Conversation.most_recent()
            if conversation:
                self.logger.info(
                    f"Most recent conversation ID: {conversation.id}"
                )
                return conversation.id
            self.logger.info("No conversations found.")
            return None
        except Exception as exc:
            self.logger.error(
                f"Error fetching most recent conversation ID: {exc}",
                exc_info=True,
            )
            return None

    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return serialized conversation metadata for service consumers."""
        conversations = Conversation.objects.filter(Conversation.id >= 1) or []
        ordered = sorted(
            conversations,
            key=lambda item: getattr(item, "id", 0),
            reverse=True,
        )
        if limit > 0:
            ordered = ordered[:limit]
        return [self._conversation_payload(item) for item in ordered]

    def get_conversation_session(
        self,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
        mark_current: bool = False,
    ) -> Dict[str, Any]:
        """Return one serialized conversation plus formatted messages."""
        conversation = self._resolve_conversation(conversation_id)
        if conversation is None:
            return {
                "conversation": None,
                "conversation_id": None,
                "messages": [],
            }

        if mark_current:
            Conversation.make_current(conversation.id)
            conversation.current = True

        messages = self.load_conversation_history(
            conversation=conversation,
            max_messages=max_messages,
        )
        return {
            "conversation": self._conversation_payload(conversation),
            "conversation_id": conversation.id,
            "messages": messages,
        }

    def summarize_conversation(
        self,
        conversation_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return one persisted or generated summary for a conversation."""
        conversation = self._conversation_by_id(conversation_id)
        if conversation is None:
            return None
        return {
            "conversation_id": conversation_id,
            "summary": self._conversation_summary(conversation),
        }

    def create_conversation(
        self,
        max_messages: int = 50,
    ) -> Dict[str, Any]:
        """Create one new current conversation and return its session."""
        conversation = Conversation.create()
        if conversation is None or getattr(conversation, "id", None) is None:
            return {
                "conversation": None,
                "conversation_id": None,
                "messages": [],
            }
        return self.get_conversation_session(
            conversation_id=conversation.id,
            max_messages=max_messages,
            mark_current=True,
        )

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete one conversation from persistent storage."""
        conversation = self._conversation_by_id(conversation_id)
        if conversation is None:
            return False
        Conversation.delete(conversation_id)
        return True

    def update_conversation_messages(
        self,
        conversation_id: int,
        messages: List[Dict[str, Any]],
    ) -> bool:
        """Persist one conversation's messages."""
        if self._conversation_by_id(conversation_id) is None:
            return False
        Conversation.objects.update(pk=conversation_id, value=list(messages))
        return True

    def update_conversation_user_data(
        self,
        conversation_id: int,
        user_data: Dict[str, Any],
    ) -> bool:
        """Persist one conversation's user-data payload."""
        if self._conversation_by_id(conversation_id) is None:
            return False
        Conversation.objects.update(
            pk=conversation_id,
            user_data=dict(user_data or {}),
        )
        return True

    def _resolve_conversation(
        self,
        conversation_id: Optional[int],
    ) -> Optional[Conversation]:
        """Resolve one conversation by id or current/most-recent fallback."""
        if conversation_id is not None:
            return self._conversation_by_id(conversation_id)

        current = self.get_current_conversation()
        if current is not None:
            return current
        return Conversation.most_recent()

    @staticmethod
    def _conversation_by_id(
        conversation_id: int,
    ) -> Optional[Conversation]:
        """Return one conversation by primary key."""
        return Conversation.objects.filter_by_first(id=conversation_id)

    def _conversation_payload(
        self,
        conversation: Conversation,
    ) -> Dict[str, Any]:
        """Serialize one conversation into JSON-safe metadata."""
        raw_messages = getattr(conversation, "value", None)
        if not isinstance(raw_messages, list):
            raw_messages = []

        return {
            "id": getattr(conversation, "id", None),
            "title": str(getattr(conversation, "title", "") or ""),
            "summary": self._conversation_summary(conversation),
            "current": bool(getattr(conversation, "current", False)),
            "timestamp": self._serialize_timestamp(
                getattr(conversation, "timestamp", None)
            ),
            "chatbot_id": getattr(conversation, "chatbot_id", None),
            "chatbot_name": str(
                getattr(conversation, "chatbot_name", "") or ""
            ),
            "user_id": getattr(conversation, "user_id", None),
            "user_name": str(getattr(conversation, "user_name", "") or ""),
            "message_count": len(raw_messages),
            "user_data": dict(getattr(conversation, "user_data", None) or {}),
        }

    def _conversation_summary(self, conversation: Conversation) -> str:
        """Return one cached or generated conversation summary."""
        summary = str(getattr(conversation, "summary", "") or "").strip()
        if summary:
            return summary

        try:
            summary = str(conversation.summarize() or "").strip()
        except Exception as exc:
            self.logger.warning(
                "Failed to summarize conversation %s: %s",
                getattr(conversation, "id", None),
                exc,
            )
            return ""

        if not summary:
            return ""

        try:
            Conversation.objects.update(conversation.id, summary=summary)
        except Exception as exc:
            self.logger.warning(
                "Failed to persist summary for conversation %s: %s",
                getattr(conversation, "id", None),
                exc,
            )
        conversation.summary = summary
        return summary

    @staticmethod
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

    def load_conversation_history(
        self,
        conversation: Optional[Conversation] = None,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
    ) -> List[Dict[str, Any]]:
        """Load and format one conversation history for display."""
        if conversation is None and conversation_id is not None:
            conversation = Conversation.objects.filter_by_first(
                id=conversation_id
            )
            if conversation is None:
                self.logger.warning(
                    f"Conversation {conversation_id} not found. Returning empty history."
                )
                return []
        elif conversation is None:
            conversation = self.get_current_conversation()

        if conversation is None:
            conversation = Conversation.most_recent()
            if conversation is None:
                self.logger.warning(
                    "No conversation found. Returning empty history."
                )
                return []
        return load_formatted_conversation_history(
            logger=self.logger,
            conversation=conversation,
            max_messages=max_messages,
            normalize_thinking_content=normalize_thinking_content,
            strip_stored_thinking_prefix=strip_stored_thinking_prefix,
            has_gpt_oss_markup=has_gpt_oss_markup,
            parse_gpt_oss_response=parse_gpt_oss_response,
        )
