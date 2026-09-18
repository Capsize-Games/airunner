"""Service-owned mixin for LLM interrupt and unload routing."""

from __future__ import annotations

from typing import Optional

from airunner_services.utils.application.enum_resolver import signal_code_proxy
from airunner_services.utils.application.get_logger import get_logger

logger = get_logger(__name__)

SignalCode = signal_code_proxy()


class LLMUnloadRoutingMixin:
    """Route LLM interrupt and unload requests to the local worker."""

    def interrupt(self) -> None:
        """Interrupt one active LLM request."""
        logger.debug("[LLM INTERRUPT] Emitting INTERRUPT_PROCESS_SIGNAL")
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    def unload(self, data: Optional[dict] = None) -> None:
        """Unload the active LLM without blocking the caller."""
        payload = dict(data or {})
        self._emit_local_unload_request(payload)

    def _emit_local_unload_request(self, payload: dict) -> None:
        """Emit one best-effort local unload request."""
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)
        self.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL, payload)
