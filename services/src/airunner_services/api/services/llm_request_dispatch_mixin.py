"""Service-owned mixin for daemon-backed LLM request dispatch."""

from __future__ import annotations

import threading
import uuid
from typing import Any, Callable, Optional

from airunner_services.daemon_connection_state import DaemonConnectionState
from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.utils.application.enum_resolver import signal_code_proxy


SignalCode = signal_code_proxy()


class LLMRequestDispatchMixin:
    """Dispatch LLM requests through daemon or local fallback paths."""

    def send_request(
        self,
        prompt,
        command: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        action: object = LLMActionType.CHAT,
        do_tts_reply: bool = True,
        node_id: Optional[str] = None,
        request_id: Optional[str] = None,
        callback: Optional[Callable[..., object]] = None,
        conversation_id: Optional[int] = None,
        **kwargs,
    ) -> None:
        """Queue one LLM request through daemon or local worker paths."""
        search_hints = kwargs.pop("search_hints", None)
        llm_request = LLMRequestDispatchMixin._prepare_llm_request(
            self,
            llm_request,
            action,
            do_tts_reply,
            kwargs,
        )
        resolved_request_id = request_id or str(uuid.uuid4())
        data = LLMRequestDispatchMixin._build_request_signal_data(
            self,
            prompt,
            command,
            llm_request,
            action,
            do_tts_reply,
            resolved_request_id,
            search_hints,
            conversation_id,
            node_id,
        )
        LLMRequestDispatchMixin._register_pending_callback(
            resolved_request_id,
            callback,
        )

        if self._send_request_via_daemon(
            prompt,
            llm_request,
            action,
            resolved_request_id,
            search_hints,
            conversation_id,
            node_id,
            signal_data=data,
        ):
            self.logger.info("LLM API: Daemon request queued")
            return

        LLMRequestDispatchMixin._emit_local_generation_request(self, data)

    def _prepare_llm_request(
        self,
        llm_request: Optional[LLMRequest],
        action: object,
        do_tts_reply: bool,
        kwargs: dict[str, Any],
    ) -> LLMRequest:
        """Normalize one request payload before dispatch."""
        system_prompt = kwargs.pop("system_prompt", None)
        llm_request = llm_request or LLMRequest.for_action(action)
        if system_prompt:
            try:
                setattr(llm_request, "system_prompt", system_prompt)
            except Exception:
                logger = getattr(self, "logger", None)
                if logger is not None:
                    logger.exception(
                        "Failed to set system_prompt on llm_request"
                    )
        if kwargs:
            logger = getattr(self, "logger", None)
            if logger is not None:
                logger.warning(
                    "LLMAPIService.send_request received unknown kwargs: "
                    f"{list(kwargs.keys())} - ignoring"
                )
        llm_request.do_tts_reply = do_tts_reply
        return llm_request

    def _build_request_signal_data(
        self,
        prompt: str,
        command: Optional[str],
        llm_request: LLMRequest,
        action: object,
        do_tts_reply: bool,
        request_id: str,
        search_hints: Optional[dict],
        conversation_id: Optional[int],
        node_id: Optional[str],
    ) -> dict[str, Any]:
        """Return one local-worker signal payload for an LLM request."""
        data = {
            "llm_request": True,
            "request_id": request_id,
            "request_data": {
                "action": action,
                "prompt": prompt,
                "command": command,
                "llm_request": llm_request,
                "do_tts_reply": do_tts_reply,
                "request_id": request_id,
            },
        }
        if search_hints is not None:
            data["request_data"]["search_hints"] = search_hints
        if conversation_id is not None:
            data["conversation_id"] = conversation_id
        if node_id is not None:
            data["node_id"] = node_id
        return data

    @staticmethod
    def _register_pending_callback(
        request_id: str,
        callback: Optional[Callable[..., object]],
    ) -> None:
        """Register one callback with the shared signal mediator."""
        if callback is None:
            return
        from airunner_services.utils.application.signal_mediator import (
            SignalMediator,
        )

        SignalMediator().register_pending_request(request_id, callback)

    def clear_history(self, **kwargs) -> None:
        """Emit one clear-history request."""
        self.emit_signal(SignalCode.LLM_CLEAR_HISTORY_SIGNAL, kwargs)

    def delete_messages_after_id(self, message_id: int) -> None:
        """Emit one request to trim conversation history after a message."""
        self.emit_signal(
            SignalCode.DELETE_MESSAGES_AFTER_ID,
            {"message_id": message_id},
        )

    def _send_request_via_daemon(
        self,
        prompt: str,
        llm_request: LLMRequest,
        action: object,
        request_id: Optional[str],
        search_hints: Optional[dict],
        conversation_id: Optional[int],
        node_id: Optional[str],
        signal_data: Optional[dict] = None,
    ) -> bool:
        """Route one request through the daemon when that client is ready."""
        client = self._daemon_client()
        if client is None or not request_id:
            return False
        if getattr(llm_request, "images", None):
            return False

        thread = threading.Thread(
            target=LLMRequestDispatchMixin._run_daemon_request_or_fallback,
            args=(
                self,
                client,
                prompt,
                llm_request,
                action,
                request_id,
                search_hints,
                conversation_id,
                node_id,
                signal_data,
            ),
            daemon=True,
        )
        thread.start()
        return True

    def _emit_local_generation_request(self, data: dict[str, Any]) -> None:
        """Emit one local-worker request when daemon routing is skipped."""
        self.emit_signal(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, data)
        self.logger.info("LLM API: Signal emitted")

    @staticmethod
    def _daemon_state_value(state: object) -> object:
        """Return one comparable daemon state value."""
        return getattr(state, "value", state)

    def _daemon_is_immediately_available(self, client) -> bool:
        """Return True when the daemon can accept one request right now."""
        if LLMRequestDispatchMixin._daemon_state_value(
            getattr(client, "state", None)
        ) == DaemonConnectionState.CONNECTED.value:
            return True
        availability_check = getattr(client, "is_available", None)
        if callable(availability_check):
            try:
                return bool(availability_check(timeout_seconds=0.2))
            except TypeError:
                return bool(availability_check())
        return bool(client.ensure_connected(auto_start=False))

    def _prewarm_tts_runtime_for_request(
        self,
        llm_request: LLMRequest,
    ) -> None:
        """Start sidecar TTS early when one daemon reply will be spoken."""
        worker_manager_getter = getattr(self, "_worker_manager", None)
        if not callable(worker_manager_getter):
            return

        worker_manager = worker_manager_getter()
        if worker_manager is None:
            return

        app_settings = getattr(worker_manager, "application_settings", None)
        if not getattr(llm_request, "do_tts_reply", False) and not bool(
            getattr(app_settings, "tts_enabled", False)
        ):
            return

        prewarm = getattr(worker_manager, "_start_tts_runtime_prewarm", None)
        if callable(prewarm):
            prewarm()

    def _run_daemon_request_or_fallback(
        self,
        client,
        prompt: str,
        llm_request: LLMRequest,
        action: object,
        request_id: str,
        search_hints: Optional[dict],
        conversation_id: Optional[int],
        node_id: Optional[str],
        signal_data: Optional[dict],
    ) -> None:
        """Use the daemon when available, else emit the local fallback."""
        if not LLMRequestDispatchMixin._daemon_is_immediately_available(
            self,
            client,
        ):
            if signal_data is not None:
                LLMRequestDispatchMixin._emit_local_generation_request(
                    self,
                    signal_data,
                )
            return

        LLMRequestDispatchMixin._prewarm_tts_runtime_for_request(
            self,
            llm_request,
        )
        self._stream_daemon_request(
            client,
            prompt,
            llm_request,
            action,
            request_id,
            search_hints,
            conversation_id,
            node_id,
        )