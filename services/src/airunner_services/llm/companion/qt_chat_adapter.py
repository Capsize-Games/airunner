"""Qt chat-stream adapter for companion turns (B13).

Tracks one in-flight companion turn and converts its B01
``CompanionStreamEvent`` values (as produced by the B12
local-inference service) into the GUI chunks the Qt chat stream
already consumes: ordered text, tool-status updates, and terminal
error/cancel chunks that settle the UI.

Qt-free on purpose: the chat widget maps these chunks onto
``LLMResponse``/tool-status signals, so this module — and its
contract tests — run with no Qt, model, network, GPU, or database.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from airunner_services.ipc.messages import EnvelopeStatus

from .contracts import (
    ERROR_INFERENCE_UNAVAILABLE,
    CallChainId,
    ChatbotId,
    CompanionErrorCode,
    CompanionStreamEvent,
    SessionId,
)
from .qt_chat_chunks import (
    cancelled_chunk,
    error_chunk,
    text_chunk,
    tool_status_chunks,
)
from .stream_events import cancelled_event


class CompanionChatAdapter:
    """Track one in-flight companion turn for the Qt chat stream."""

    def __init__(
        self,
        chatbot_id: Optional[ChatbotId] = None,
        session_id: Optional[SessionId] = None,
    ) -> None:
        self._chatbot_id = chatbot_id
        self._session_id = session_id
        self._call_chain_id: Optional[CallChainId] = None
        self._request_id: Optional[str] = None
        self._conversation_id: Optional[int] = None
        self._next_sequence = 0
        self._emitted_visible = 0

    @property
    def bot_session(self) -> Tuple[Optional[ChatbotId], Optional[SessionId]]:
        """Return the (chatbot, session) this adapter streams for."""
        return (self._chatbot_id, self._session_id)

    @property
    def active_call_chain_id(self) -> Optional[CallChainId]:
        """Return the in-flight turn's chain, or None when idle."""
        return self._call_chain_id

    @property
    def conversation_id(self) -> Optional[int]:
        """Return the conversation the active turn streams into."""
        return self._conversation_id

    def begin_turn(
        self,
        call_chain_id: CallChainId,
        request_id: str,
        conversation_id: Optional[int] = None,
    ) -> None:
        """Register one companion turn (the send-side entrypoint)."""
        if self._call_chain_id is not None:
            raise ValueError(
                "companion turn already active; cancel or switch "
                "conversations before beginning another"
            )
        self._call_chain_id = call_chain_id
        self._request_id = request_id
        self._conversation_id = conversation_id
        self._next_sequence = 0
        self._emitted_visible = 0

    def adapt(self, event: CompanionStreamEvent) -> List[Dict[str, Any]]:
        """Convert one turn event to GUI chunks, preserving order."""
        if (
            self._call_chain_id is None
            or event.call_chain_id != self._call_chain_id
        ):
            return []
        if event.sequence < self._next_sequence:
            return []
        self._next_sequence = event.sequence + 1
        if event.status == EnvelopeStatus.FAILED:
            return [self._failed_chunk(event)]
        if event.status == EnvelopeStatus.CANCELLED:
            chunk = self._cancelled_chunk(event.sequence)
            self._settle()
            return [chunk]
        chunks = tool_status_chunks(
            event, self._request_id, self._conversation_id
        )
        if event.delta_text or event.final:
            chunks.append(
                text_chunk(
                    event,
                    self._request_id,
                    self._conversation_id,
                    self._first_visible(),
                )
            )
        if event.final:
            self._settle()
        return chunks

    def cancel_turn(
        self, call_chain_id: Optional[CallChainId] = None
    ) -> List[Dict[str, Any]]:
        """Cancel the active turn; late events for it are dropped."""
        if self._call_chain_id is None:
            return []
        if call_chain_id is not None and call_chain_id != self._call_chain_id:
            return []
        event = cancelled_event(self._call_chain_id, self._next_sequence)
        chunk = self._cancelled_chunk(event.sequence)
        self._settle()
        return [chunk]

    def switch_conversation(
        self,
        conversation_id: Optional[int],
        chatbot_id: Optional[ChatbotId] = None,
        session_id: Optional[SessionId] = None,
    ) -> List[Dict[str, Any]]:
        """Settle any in-flight turn and restore bot/session state."""
        chunks = self.cancel_turn()
        self._conversation_id = conversation_id
        if chatbot_id is not None:
            self._chatbot_id = chatbot_id
        if session_id is not None:
            self._session_id = session_id
        return chunks

    def _settle(self) -> None:
        """Forget the active turn; its late events are dropped."""
        self._call_chain_id = None
        self._request_id = None
        self._next_sequence = 0
        self._emitted_visible = 0

    def _first_visible(self) -> bool:
        """Mirror the daemon: the first visible chunk opens a turn."""
        first = self._emitted_visible == 0
        self._emitted_visible += 1
        return first

    def _failed_chunk(self, event: CompanionStreamEvent) -> Dict[str, Any]:
        """Return the terminal chunk for a failed turn event."""
        error = event.error or CompanionErrorCode(
            code=ERROR_INFERENCE_UNAVAILABLE,
            detail="companion turn failed",
            retryable=True,
        )
        chunk = error_chunk(
            event,
            error,
            self._request_id,
            self._conversation_id,
            self._first_visible(),
        )
        self._settle()
        return chunk

    def _cancelled_chunk(self, sequence: int) -> Dict[str, Any]:
        """Return the terminal chunk for a cancelled turn."""
        assert self._call_chain_id is not None
        return cancelled_chunk(
            self._call_chain_id,
            sequence,
            self._request_id,
            self._conversation_id,
            self._first_visible(),
        )


__all__ = ["CompanionChatAdapter"]
