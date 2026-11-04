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
from airunner_services.runtimes.signal_runtime_client import (
    DEFAULT_TIMEOUT_SECONDS,
    HealthProvider,
    _SignalRuntimeClient,
    _resolve_model_type,
)
from airunner_services.utils.application.get_logger import get_logger

logger = get_logger(__name__)

DEFAULT_PROVIDER = "local"

#: Largest decoded audio clip accepted by the local-fallback STT path.
MAX_LOCAL_FALLBACK_AUDIO_BYTES = 15 * 1024 * 1024


def _build_stt_service() -> Any:
    """Create the default STT API service lazily."""
    from airunner_services.api.services.stt_services import STTAPIService

    return STTAPIService()


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
        from airunner_common.contract_enums import SignalCode

        logger.warning(
            "STT cancel for request %s is best-effort only", request_id
        )
        self._emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _load_model(self, request_id: str) -> ResponseEnvelope:
        """Load the local STT model."""
        from airunner_common.contract_enums import ModelStatus, SignalCode

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
        from airunner_common.contract_enums import ModelStatus, SignalCode

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
        """Run a transcription request through the working response signal.

        Registration, emit and wait all hold the signal lock: the
        mediator is shared, so without it a concurrent transcription
        registers an identical handler and each call can consume the
        other's response.
        """
        from airunner_common.contract_enums import SignalCode

        invocation = STTInvocationRequest.model_validate(request.payload)
        try:
            audio_bytes = base64.b64decode(invocation.audio_b64, validate=True)
        except Exception:
            return self._failure_response(
                request.request_id,
                "stt_invalid_audio",
                "Invalid base64 audio payload",
            )
        if len(audio_bytes) > MAX_LOCAL_FALLBACK_AUDIO_BYTES:
            return self._failure_response(
                request.request_id,
                "stt_invalid_audio",
                "Audio payload exceeds the size budget",
            )

        transcription_queue: Queue[Any] = Queue()

        def on_transcription(data: dict[str, Any]) -> None:
            if data.get("request_id", request.request_id) != request.request_id:
                return
            transcription = data.get("transcription")
            if transcription is not None:
                transcription_queue.put(transcription)

        with self._signal_lock:
            self._mediator.register(
                SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
                on_transcription,
            )
            try:
                self._emit_signal(
                    SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
                    {"item": audio_bytes, "request_id": request.request_id},
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
            except Exception as exc:
                # A missing local STT backend (no model configured, no ML
                # runtime) surfaces here as a raised error; report it as a
                # failed envelope like the art fallback does (issue #2243)
                # instead of letting the route turn it into a bare 500.
                return self._failure_response(
                    request.request_id,
                    "stt_invoke_failed",
                    str(exc),
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
