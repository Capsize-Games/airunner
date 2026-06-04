"""Service-owned mixin for LLM interrupt and unload routing."""

from __future__ import annotations

import threading
from typing import Optional

from airunner_services.contract_enums import ModelStatus
from airunner_services.utils.application.enum_resolver import signal_code_proxy

SignalCode = signal_code_proxy()


class LLMUnloadRoutingMixin:
    """Route LLM interrupt and unload requests to daemon or local paths."""

    def interrupt(self) -> None:
        """Interrupt one active LLM request."""
        client = self._daemon_client()
        if client is not None:
            try:
                client.interrupt_llm()
                return
            except RuntimeError:
                pass

        print("[LLM INTERRUPT] Emitting INTERRUPT_PROCESS_SIGNAL")
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    def unload(self, data: Optional[dict] = None) -> None:
        """Unload the active LLM without blocking the caller."""
        payload = dict(data or {})
        if LLMUnloadRoutingMixin._local_llm_should_handle_unload(self):
            self._emit_local_unload_request(payload)
            return

        client = self._daemon_client()
        if client is None:
            self._emit_local_unload_request(payload)
            return

        thread = threading.Thread(
            target=LLMUnloadRoutingMixin._run_daemon_unload,
            args=(self, client, payload),
            daemon=True,
        )
        thread.start()

    def _emit_local_unload_request(self, payload: dict) -> None:
        """Emit one best-effort local unload request."""
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)
        self.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL, payload)

    def _local_llm_should_handle_unload(self) -> bool:
        """Return True when the GUI-local worker owns the live LLM."""
        worker_manager_getter = getattr(self, "_worker_manager", None)
        if not callable(worker_manager_getter):
            return False

        worker_manager = worker_manager_getter()
        if worker_manager is None:
            return False

        worker = getattr(worker_manager, "_llm_generate_worker", None)
        if worker is None:
            return False

        status_getter = getattr(worker, "current_model_status", None)
        if callable(status_getter):
            try:
                status = status_getter()
            except Exception:
                status = None
            if status in (ModelStatus.LOADING, ModelStatus.LOADED):
                return True

        return getattr(worker, "_pending_llm_request", None) is not None

    def _run_daemon_unload(self, client, payload: dict) -> None:
        """Interrupt and queue one daemon-side LLM unload."""
        try:
            client.interrupt_llm()
        except RuntimeError:
            pass

        try:
            client.unload_local_llm(auto_start=False)
        except RuntimeError:
            self._emit_local_unload_request(payload)