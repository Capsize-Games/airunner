"""Service-owned mixin for in-process LLM request dispatch."""

from __future__ import annotations

import uuid
from typing import Any, Callable, Optional

from airunner_common.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.utils.application.enum_resolver import signal_code_proxy


SignalCode = signal_code_proxy()


class LLMRequestDispatchMixin:
    """Dispatch LLM requests to the in-process local generation worker."""

    @staticmethod
    def _default_gguf_runtime_profile(
        llm_request: Optional[LLMRequest],
        do_tts_reply: bool,
    ) -> Optional[str]:
        """Return the implicit GGUF runtime profile for one request."""
        if llm_request is None:
            return None

        profile = getattr(llm_request, "gguf_runtime_profile", None)
        if isinstance(profile, str):
            profile = profile.strip() or None
        if profile:
            return profile

        model_service = getattr(llm_request, "model_service", None)
        if isinstance(model_service, str):
            model_service = model_service.strip().lower() or None
        if do_tts_reply and model_service in (None, "local"):
            return "combined_tts"
        return None

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
        """Queue one LLM request on the in-process local worker path."""
        search_hints = kwargs.pop("search_hints", None)
        llm_request = LLMRequestDispatchMixin._prepare_llm_request(
            self,
            llm_request,
            action,
            do_tts_reply,
            kwargs,
        )
        resolved_request_id = request_id or str(uuid.uuid4())
        tracker = getattr(self, "_register_request_tts_preference", None)
        if callable(tracker):
            tracker(resolved_request_id, do_tts_reply)
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
        llm_request.gguf_runtime_profile = (
            LLMRequestDispatchMixin._default_gguf_runtime_profile(
                llm_request,
                do_tts_reply,
            )
        )
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

    def _emit_local_generation_request(self, data: dict[str, Any]) -> None:
        """Emit one local-worker request for in-process generation."""
        self.emit_signal(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, data)
        self.logger.info("LLM API: Signal emitted")
