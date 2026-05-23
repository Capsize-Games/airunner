"""In-process TTS executor for the TTS sidecar daemon.

This module replaces LocalFallbackTTSClient for the TTS sidecar subprocess.
When AIRUNNER_TTS_SIDECAR_PROCESS=1, the sidecar daemon handles TTS requests
via this executor instead of routing through the signal-based API services.

The executor bridges the runtime contract (TTSInvocationRequest) to the
in-process TTS engine without depending on the legacy signal mediator.
"""

from __future__ import annotations

import base64
import io
from queue import Empty, Queue
from typing import Any, Callable, Optional

from airunner.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    TTSInvocationRequest,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute

DEFAULT_PROVIDER = "local"
DEFAULT_TIMEOUT_SECONDS = 120.0
HealthProvider = Callable[[], RuntimeHealthStatus]


def _build_signal_mediator() -> Any:
    """Create the default signal mediator lazily."""
    from airunner.utils.application.signal_mediator import SignalMediator

    return SignalMediator()


def _build_tts_service() -> Any:
    """Create the default TTS API service lazily."""
    from airunner.components.tts.api.tts_services import TTSAPIService

    return TTSAPIService()


def _resolve_model_type(name: str) -> Any:
    """Resolve a model type lazily to avoid eager imports."""
    from airunner.enums import ModelType

    return getattr(ModelType, name)


def _model_health_status(model_status: Any) -> RuntimeHealthStatus:
    """Translate application model status into runtime health status."""
    from airunner.enums import ModelStatus

    status_map = {
        None: RuntimeHealthStatus.UNKNOWN,
        ModelStatus.LOADING: RuntimeHealthStatus.STARTING,
        ModelStatus.LOADED: RuntimeHealthStatus.READY,
        ModelStatus.READY: RuntimeHealthStatus.READY,
        ModelStatus.FAILED: RuntimeHealthStatus.FAILED,
        ModelStatus.UNLOADED: RuntimeHealthStatus.STOPPED,
    }
    return status_map.get(model_status, RuntimeHealthStatus.UNKNOWN)


def _model_status_value(model_status: Any) -> str:
    """Return a stable string representation of a model status."""
    return getattr(model_status, "value", "")


class _SignalRuntimeClient(RuntimeClient):
    """Common helpers for signal-backed local execution clients."""

    def __init__(
        self,
        runtime: RuntimeKind,
        provider: str,
        *,
        signal_source: Any = None,
        mediator: Any = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        health_provider: Optional[HealthProvider] = None,
        supports_streaming: bool = False,
        allows_model_control: bool = True,
        model_type: Any = None,
    ) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=runtime,
            provider=provider,
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
            supports_streaming=supports_streaming,
            allows_model_control=allows_model_control,
        )
        self._signal_source = signal_source or _build_signal_mediator()
        self._mediator = mediator or _build_signal_mediator()
        self._timeout_seconds = timeout_seconds
        self._health_provider = health_provider
        self._last_model_status = None
        self._model_type = model_type

    def healthcheck(self) -> RuntimeHealth:
        """Return current health state for the runtime client."""
        if self._health_provider is not None:
            return RuntimeHealth(
                descriptor=self.descriptor,
                status=self._health_provider(),
            )
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=_model_health_status(self._last_model_status),
            details=_model_status_value(self._last_model_status),
            metadata=self._status_metadata(),
        )

    def _emit_signal(self, code: Any, data: Optional[dict[str, Any]] = None):
        """Emit a signal through the configured source."""
        emitter = getattr(self._signal_source, "emit_signal", None)
        if emitter is not None:
            emitter(code, data or {})
            return
        self._mediator.emit_signal(code, data or {})

    def _status_response(self, request_id: str) -> ResponseEnvelope:
        """Return a response envelope for the current client status."""
        health = self.healthcheck()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"status": health.status.value},
            metadata=health.metadata,
        )

    def _status_metadata(self) -> dict[str, Any]:
        """Return cached model metadata when available."""
        if self._last_model_status is None:
            return {}
        return {"model_status": _model_status_value(self._last_model_status)}

    def _cache_status(self, model_status: Any) -> None:
        """Track the most recent model status for health checks."""
        self._last_model_status = model_status

    def _matches_model(self, model: Any) -> bool:
        """Return True when a status event targets this client's model."""
        if self._model_type is None:
            return True
        expected = getattr(self._model_type, "value", self._model_type)
        actual = getattr(model, "value", model)
        return actual == expected

    def _wait_for_model_status(
        self,
        request_id: str,
        *,
        emit_code: Any,
        emit_data: Optional[dict[str, Any]],
        success_statuses: tuple[Any, ...],
        timeout_code: str,
        failure_code: str,
        action_name: str,
    ) -> ResponseEnvelope:
        """Emit a control signal and wait for the matching model status."""
        from airunner.enums import ModelStatus, SignalCode

        status_queue: Queue[Any] = Queue()

        def on_status_changed(data: dict[str, Any]) -> None:
            model = data.get("model")
            if not self._matches_model(model):
                return
            status = data.get("status")
            self._cache_status(status)
            if status in success_statuses or status is ModelStatus.FAILED:
                status_queue.put(status)

        self._mediator.register(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            on_status_changed,
        )
        try:
            self._emit_signal(emit_code, emit_data)
            try:
                status = status_queue.get(timeout=self._timeout_seconds)
            except Empty:
                return self._failure_response(
                    request_id,
                    timeout_code,
                    f"{action_name} timed out",
                    retryable=True,
                )
        finally:
            self._mediator.unregister(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                on_status_changed,
            )

        if status is ModelStatus.FAILED:
            return self._failure_response(
                request_id,
                failure_code,
                f"{action_name} failed",
            )
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"model_status": _model_status_value(status)},
            metadata=self._status_metadata(),
        )

    @staticmethod
    def _failure_response(
        request_id: str,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> ResponseEnvelope:
        """Create a failure response envelope."""
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.FAILED,
            error=ErrorEnvelope(
                code=code,
                message=message,
                retryable=retryable,
            ),
        )


class SidecarTTSExecutor(_SignalRuntimeClient):
    """Execute TTS in-process for the TTS sidecar daemon.

    Receives TTSInvocationRequest envelopes and dispatches them directly
    to the TTS engine via the existing signal infrastructure. This
    replaces LocalFallbackTTSClient for sidecar subprocesses.
    """

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
            raise ValueError("SidecarTTSExecutor only supports TTS")
        if request.action is RuntimeAction.STATUS:
            return self._status_response(request.request_id)
        if request.action is RuntimeAction.LOAD_MODEL:
            return self._load_model(request.request_id)
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return self._unload_model(request.request_id)
        if request.action is not RuntimeAction.INVOKE:
            raise ValueError("SidecarTTSExecutor only supports invoke")
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
        from airunner.enums import SignalCode

        self._emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )

    def _load_model(self, request_id: str) -> ResponseEnvelope:
        """Enable and load the local TTS model."""
        from airunner.enums import ModelStatus, SignalCode

        return self._wait_for_model_status(
            request_id,
            emit_code=SignalCode.TTS_ENABLE_SIGNAL,
            emit_data={},
            success_statuses=(ModelStatus.LOADED, ModelStatus.READY),
            timeout_code="tts_load_timeout",
            failure_code="tts_load_failed",
            action_name="TTS load",
        )

    def _unload_model(self, request_id: str) -> ResponseEnvelope:
        """Disable and unload the local TTS model."""
        from airunner.enums import ModelStatus, SignalCode

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
        from airunner.enums import ModelStatus

        if worker is None:
            return None
        manager = getattr(worker, "tts", None)
        if manager is None:
            initializer = getattr(
                worker, "_initialize_tts_model_manager", None
            )
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
        from airunner.components.tts.managers.tts_request import (
            OpenVoiceTTSRequest,
        )
        from airunner.enums import TTSModel

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
    def _tts_model_type(
        invocation: TTSInvocationRequest, worker
    ) -> Optional[str]:
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
        from airunner.enums import SignalCode

        self._emit_signal(
            SignalCode.TTS_QUEUE_SIGNAL,
            {"message": text, "is_end_of_message": True},
        )


def register_sidecar_tts_executor(
    registry: RuntimeRegistry,
    tts_client: Optional[RuntimeClient] = None,
) -> RuntimeRegistry:
    """Register the in-process TTS executor under the local fallback route."""
    client = tts_client or SidecarTTSExecutor()
    routes = (
        RuntimeRoute(RuntimeKind.TTS, provider=DEFAULT_PROVIDER),
        RuntimeRoute(
            RuntimeKind.TTS,
            provider=DEFAULT_PROVIDER,
            deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
        ),
    )
    for route in routes:
        registry.register(route, client)
    return registry
