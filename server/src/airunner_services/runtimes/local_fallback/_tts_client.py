"""Local fallback TTS runtime client."""
from __future__ import annotations

import base64
import io
from typing import Any, Optional

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.contracts import (
    RuntimeAction,
    RuntimeKind,
    TTSInvocationRequest,
)
from airunner_services.runtimes.local_fallback._base import (
    DEFAULT_PROVIDER,
    DEFAULT_TIMEOUT_SECONDS,
    HealthProvider,
    _build_signal_mediator,
    _build_tts_service,
    _model_status_value,
    _resolve_model_type,
    _SignalRuntimeClient,
)

class LocalFallbackTTSClient(_SignalRuntimeClient):
    """Bridge TTS runtime requests to the existing playback-oriented path."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        signal_source: Any = None,
        mediator: Any = None,
        health_provider: Optional[HealthProvider] = None,
    ) -> None:
        super().__init__(
            RuntimeKind.TTS,
            provider,
            signal_source=signal_source or _build_tts_service(),
            mediator=mediator,
            timeout_seconds=timeout_seconds,
            health_provider=health_provider,
            model_type=_resolve_model_type("TTS"),
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Queue playback or execute TTS model-control actions."""
        if request.runtime is not RuntimeKind.TTS:
            raise ValueError("LocalFallbackTTSClient only supports TTS")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("LocalFallbackTTSClient only supports invoke")
        invocation = TTSInvocationRequest.model_validate(request.payload)
        if self._headless_tts_worker() is not None:
            return self._invoke_headless_runtime(
                request.request_id,
                invocation,
            )

        return self._invoke_playback_runtime(request.request_id, invocation)

    def _invoke_headless_runtime(
        self,
        request_id: str,
        invocation: TTSInvocationRequest,
    ) -> ResponseEnvelope:
        """Return audio from one headless runtime instead of local playback."""
        audio_b64 = self._audio_payload(invocation)
        if audio_b64 is not None:
            return ResponseEnvelope(
                request_id=request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={
                    "accepted": True,
                    "audio_b64": audio_b64,
                },
                metadata={"stream": False},
            )
        return self._failure_response(
            request_id,
            "tts_audio_unavailable",
            "Headless TTS runtime could not render audio",
            retryable=True,
        )

    def _invoke_playback_runtime(
        self,
        request_id: str,
        invocation: TTSInvocationRequest,
    ) -> ResponseEnvelope:
        """Queue playback for one local interactive runtime."""
        self._speak(invocation.text)
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"accepted": True},
            metadata={"stream": False},
        )

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Interrupt queued or active TTS playback on a best-effort basis."""
        from airunner_services.contract_enums import SignalCode

        self._emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _load_model(self, request_id: str) -> ResponseEnvelope:
        """Enable and load the local TTS model."""
        from airunner_services.contract_enums import ModelStatus, SignalCode

        worker = self._headless_tts_worker()
        if worker is not None:
            load_tts = getattr(worker, "_load_tts", None)
            current_status = getattr(worker, "_current_tts_status", None)
            if not callable(load_tts) or not callable(current_status):
                return self._failure_response(
                    request_id,
                    "tts_load_failed",
                    "Headless TTS worker is unavailable",
                )

            load_tts()
            status = current_status()
            self._cache_status(status)
            if status in (ModelStatus.LOADED, ModelStatus.READY):
                return ResponseEnvelope(
                    request_id=request_id,
                    status=EnvelopeStatus.SUCCEEDED,
                    payload={"model_status": _model_status_value(status)},
                    metadata=self._status_metadata(),
                )
            if status is ModelStatus.FAILED:
                return self._failure_response(
                    request_id,
                    "tts_load_failed",
                    "TTS load failed",
                )
            return self._failure_response(
                request_id,
                "tts_load_failed",
                "TTS did not reach a loaded state",
                retryable=True,
            )

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.TTS_ENABLE_SIGNAL,
            emit_data={
                "source": "runtime_control",
                "request_scoped": True,
            },
            success_statuses=(ModelStatus.LOADED, ModelStatus.READY),
            timeout_code="tts_load_timeout",
            failure_code="tts_load_failed",
            action_name="TTS load",
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Disable and unload the local TTS model."""
        from airunner_services.contract_enums import ModelStatus, SignalCode

        worker = self._headless_tts_worker()
        if worker is not None:
            unload_tts = getattr(worker, "_unload_tts", None)
            current_status = getattr(worker, "_current_tts_status", None)
            if not callable(unload_tts) or not callable(current_status):
                return self._failure_response(
                    request_id,
                    "tts_unload_failed",
                    "Headless TTS worker is unavailable",
                )

            unload_tts()
            status = current_status()
            self._cache_status(status)
            if status is ModelStatus.UNLOADED:
                return ResponseEnvelope(
                    request_id=request_id,
                    status=EnvelopeStatus.SUCCEEDED,
                    payload={"model_status": _model_status_value(status)},
                    metadata=self._status_metadata(),
                )
            if status is ModelStatus.FAILED:
                return self._failure_response(
                    request_id,
                    "tts_unload_failed",
                    "TTS unload failed",
                )
            return self._failure_response(
                request_id,
                "tts_unload_failed",
                "TTS did not unload cleanly",
                retryable=True,
            )

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.TTS_DISABLE_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.UNLOADED,),
            timeout_code="tts_unload_timeout",
            failure_code="tts_unload_failed",
            action_name="TTS unload",
        )

    def _audio_payload(
        self,
        invocation: TTSInvocationRequest,
    ) -> Optional[str]:
        """Return base64 WAV audio when headless synthesis is available."""
        audio_bytes = self._render_audio_bytes(invocation)
        if not audio_bytes:
            return None
        return base64.b64encode(audio_bytes).decode("ascii")

    def _render_audio_bytes(
        self,
        invocation: TTSInvocationRequest,
    ) -> Optional[bytes]:
        """Render one TTS request to WAV bytes in headless mode."""
        worker = self._headless_tts_worker()
        manager = self._tts_manager(worker)
        request = self._tts_request(invocation, worker)
        if worker is None or manager is None or request is None:
            return None
        audio = manager.generate(request)
        if audio is None:
            return None
        return self._encode_audio(audio, self._sample_rate(manager))

    def _headless_tts_worker(self):
        """Return the headless TTS worker when one exists."""
        worker_manager = getattr(self._signal_source, "_worker_manager", None)
        if worker_manager is None:
            return None
        return getattr(worker_manager, "tts_generator_worker", None)

    def _tts_manager(self, worker):
        """Return one loaded TTS manager from the headless worker."""
        from airunner_services.contract_enums import ModelStatus

        if worker is None:
            return None
        manager = getattr(worker, "tts", None)
        if manager is None:
            initializer = getattr(worker, "_initialize_tts_model_manager", None)
            if callable(initializer):
                initializer()
            manager = getattr(worker, "tts", None)
        if manager is None:
            return None
        status_getter = getattr(worker, "_current_tts_status", None)
        status = status_getter() if callable(status_getter) else None
        if status not in (ModelStatus.LOADED, ModelStatus.READY):
            loaded = manager.load()
            if loaded is False:
                return None
        return manager

    def _tts_request(self, invocation: TTSInvocationRequest, worker):
        """Return one TTS request only for in-memory audio-capable models."""
        from airunner_services.requests.tts_request import (
            OpenVoiceTTSRequest,
        )
        from airunner_services.contract_enums import TTSModel

        if self._tts_model_type(invocation, worker) != (
            TTSModel.OPENVOICE.value.lower()
        ):
            return None
        chatbot = getattr(worker, "chatbot", None)
        return OpenVoiceTTSRequest(
            message=invocation.text,
            gender=getattr(chatbot, "gender", "Male"),
        )

    @staticmethod
    def _tts_model_type(invocation: TTSInvocationRequest, worker) -> Optional[str]:
        """Return the active TTS model type as a normalized string."""
        resolver = getattr(worker, "_active_tts_model", None)
        active_model = resolver() if callable(resolver) else None
        if active_model:
            return str(active_model).strip().lower()
        metadata = invocation.metadata or {}
        model_type = metadata.get("model_type")
        if model_type:
            return str(model_type).strip().lower()
        return None

    @staticmethod
    def _sample_rate(manager) -> int:
        """Return the sampling rate for one synthesized audio buffer."""
        converter = getattr(manager, "tone_color_converter", None)
        hps = getattr(converter, "hps", None)
        data = getattr(hps, "data", None)
        return int(getattr(data, "sampling_rate", 24000))

    @staticmethod
    def _encode_audio(audio: Any, sample_rate: int) -> bytes:
        """Encode one waveform as WAV bytes."""
        import soundfile as sf

        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format="WAV")
        return buffer.getvalue()

    def _speak(self, text: str) -> None:
        """Queue a TTS request using the current playback service."""
        if hasattr(self._signal_source, "play_audio"):
            self._signal_source.play_audio(text)
            return
        from airunner_services.contract_enums import SignalCode

        self._emit_signal(
            SignalCode.TTS_QUEUE_SIGNAL,
            {"message": text, "is_end_of_message": True},
        )
