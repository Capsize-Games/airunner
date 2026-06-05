"""Service-owned mixin for LLM conversation and provider-state orchestration."""

from __future__ import annotations

from typing import Dict, Optional

from airunner_services.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.database.session import session_scope
from airunner_services.utils.application.enum_resolver import signal_code_proxy

SignalCode = signal_code_proxy()


class LLMConversationServiceMixin:
    """Provide conversation and provider state helpers for the LLM API."""

    def list_conversations(self, limit: int = 50) -> list[Dict]:
        """Return serialized conversation metadata through the service API."""
        client = self._available_daemon_client()
        if client is not None:
            return client.list_conversations(limit=limit, auto_start=False)
        return self._conversation_history_manager().list_conversations(
            limit=limit
        )

    def get_conversation_session(
        self,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
    ) -> Dict:
        """Return one conversation session without changing the selection."""
        client = self._available_daemon_client()
        if client is not None:
            return client.get_conversation_session(
                conversation_id=conversation_id,
                max_messages=max_messages,
                auto_start=False,
            )
        return self._conversation_history_manager().get_conversation_session(
            conversation_id=conversation_id,
            max_messages=max_messages,
        )

    def summarize_conversation(self, conversation_id: int) -> str:
        """Return one summary for a conversation through the service API."""
        client = self._available_daemon_client()
        if client is not None:
            payload = client.summarize_conversation(
                conversation_id,
                auto_start=False,
            )
            return str(payload.get("summary", "") or "")

        payload = self._conversation_history_manager().summarize_conversation(
            conversation_id
        )
        if payload is None:
            return ""
        return str(payload.get("summary", "") or "")

    def converation_deleted(self, conversation_id: int) -> None:
        """Emit one conversation-deleted signal."""
        self.emit_signal(
            SignalCode.CONVERSATION_DELETED,
            {"conversation_id": conversation_id},
        )

    def _persist_provider_fields(self, **fields: object) -> Dict:
        """Persist provider fields in the shared LLM generator settings row."""
        with session_scope() as session:
            settings = session.query(LLMGeneratorSettings).first()
            if settings is None:
                settings = LLMGeneratorSettings()
                session.add(settings)
                session.flush()
            for key, value in fields.items():
                setattr(settings, key, value)

        updater = getattr(self, "update_llm_generator_settings", None)
        if callable(updater):
            updater(**fields)
        return dict(fields)

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete one conversation through the service API."""
        client = self._available_daemon_client()
        if client is not None:
            payload = client.delete_conversation(
                conversation_id,
                auto_start=False,
            )
            deleted = bool(payload.get("deleted"))
        else:
            deleted = self._conversation_history_manager().delete_conversation(
                conversation_id
            )

        if deleted:
            self.converation_deleted(conversation_id)
        return deleted

    def model_changed(self, model_service: str) -> None:
        """Persist and emit one provider change request."""
        self._persist_provider_fields(model_service=model_service)
        self.emit_signal(
            SignalCode.LLM_MODEL_CHANGED,
            {
                "model_service": model_service,
                "reload_runtime": False,
            },
        )

    def set_provider_model(
        self,
        model_service: str,
        model_id: str,
    ) -> Dict:
        """Persist one remote-provider model selection through the service."""
        return self._persist_provider_fields(
            model_service=model_service,
            model_version=model_id,
            model_id=model_id,
            model_path="",
        )

    def reload_rag(self, target_files: Optional[list[str]] = None) -> None:
        """Emit one RAG reload request through the signal bus."""
        self.emit_signal(
            SignalCode.RAG_RELOAD_INDEX_SIGNAL,
            {"target_files": target_files} if target_files else None,
        )

    def load_conversation(self, conversation_id: int) -> Dict:
        """Emit one selected conversation payload through the signal bus."""
        payload = LLMConversationServiceMixin._selected_conversation_payload(
            self,
            conversation_id,
        )
        self.emit_signal(SignalCode.QUEUE_LOAD_CONVERSATION, payload)
        return payload

    def _selected_conversation_payload(
        self,
        conversation_id: Optional[int],
        max_messages: int = 50,
    ) -> Dict:
        """Return one signal payload for a selected conversation session."""
        if conversation_id is None:
            session = self.get_conversation_session(max_messages=max_messages)
        else:
            session = self._select_conversation_session(
                conversation_id,
                max_messages=max_messages,
            )

        payload = dict(session or {})
        resolved_id = payload.get("conversation_id") or conversation_id
        payload.update(
            {
                "action": "load_conversation",
                "conversation_id": resolved_id,
                "index": resolved_id,
            }
        )
        return payload

    def _select_conversation_session(
        self,
        conversation_id: int,
        max_messages: int,
    ) -> Dict:
        """Return one selected conversation session from daemon or local state."""
        client = self._available_daemon_client()
        if client is not None:
            return client.select_conversation(
                conversation_id,
                max_messages=max_messages,
                auto_start=False,
            )

        return self._conversation_history_manager().get_conversation_session(
            conversation_id=conversation_id,
            max_messages=max_messages,
            mark_current=True,
        )

    def _available_daemon_client(self):
        """Return the live daemon client when the daemon is already reachable."""
        client = self._daemon_client()
        if client is None:
            return None
        if type(self)._daemon_is_immediately_available(self, client):
            return client
        return None

    @staticmethod
    def _conversation_history_manager() -> ConversationHistoryManager:
        """Return one local conversation history manager."""
        return ConversationHistoryManager()
