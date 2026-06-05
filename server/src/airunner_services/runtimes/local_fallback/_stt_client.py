"""Local fallback STT runtime client."""
from __future__ import annotations

import base64
from queue import Empty, Queue
from typing import Any, Optional

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.contracts import (
    RuntimeAction,
    RuntimeKind,
    STTInvocationRequest,
)
from airunner_services.runtimes.local_fallback._base import (
    DEFAULT_PROVIDER,
    DEFAULT_TIMEOUT_SECONDS,
    HealthProvider,
    _build_stt_service,
    _resolve_model_type,
    _SignalRuntimeClient,
)

class LocalFallbackSTTClient(_SignalRuntimeClient):
    """Bridge STT runtime requests to the current synchronous signal path."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        signal_source: Any = None,
        mediator: Any = None,
        health_provider: Optional[HealthProvider] = None,
    ) -> None:
        super().__init__(
            RuntimeKind.STT,
            provider,
            signal_source=signal_source or _build_stt_service(),
            mediator=mediator,
            timeout_seconds=timeout_seconds,
            health_provider=health_provider,
            model_type=_resolve_model_type("STT"),
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute STT invocation or model-control requests."""
        if request.runtime is not RuntimeKind.STT:
            raise ValueError("LocalFallbackSTTClient only supports STT")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("LocalFallbackSTTClient only supports invoke")
        return self._transcribe(request)

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Interrupt an STT request on a best-effort basis."""
        from airunner_services.contract_enums import SignalCode

        self._emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _load_model(self, request_id: str) -> ResponseEnvelope:
        """Load the local STT model."""
        from airunner_services.contract_enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.STT_LOAD_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.LOADED, ModelStatus.READY),
            timeout_code="stt_load_timeout",
            failure_code="stt_load_failed",
            action_name="STT load",
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Unload the local STT model."""
        from airunner_services.contract_enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.STT_UNLOAD_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.UNLOADED,),
            timeout_code="stt_unload_timeout",
            failure_code="stt_unload_failed",
            action_name="STT unload",
        )

    def _transcribe(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Run a transcription request through the working response signal."""
        from airunner_services.contract_enums import SignalCode

        invocation = STTInvocationRequest.model_validate(request.payload)
        try:
            audio_bytes = base64.b64decode(invocation.audio_b64, validate=True)
        except Exception:
            return self._failure_response(
                request.request_id,
                "stt_invalid_audio",
                "Invalid base64 audio payload",
            )

        transcription_queue: Queue[Any] = Queue()

        def on_transcription(data: dict[str, Any]) -> None:
            transcription = data.get("transcription")
            if transcription is not None:
                transcription_queue.put(transcription)

        self._mediator.register(
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
            on_transcription,
        )
        try:
            self._emit_signal(
                SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
                {"item": audio_bytes},
            )
            try:
                transcription = transcription_queue.get(
                    timeout=self._timeout_seconds
                )
            except Empty:
                return self._failure_response(
                    request.request_id,
                    "stt_timeout",
                    "Timed out waiting for STT response",
                    retryable=True,
                )
        finally:
            self._mediator.unregister(
                SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
                on_transcription,
            )

        payload = self._transcription_payload(transcription, invocation.language)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload=payload,
        )

    @staticmethod
    def _transcription_payload(
        transcription: Any,
        language: Optional[str],
    ) -> dict[str, Any]:
        """Normalize the current STT response payload shape."""
        if isinstance(transcription, dict):
            return {
                "text": transcription.get("text")
                or transcription.get("transcription", ""),
                "language": transcription.get("language") or language,
            }
        return {"text": str(transcription), "language": language}
