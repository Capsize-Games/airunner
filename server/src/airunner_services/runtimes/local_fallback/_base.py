"""Shared helpers and base class for local fallback runtime clients."""
from __future__ import annotations

import base64
import io
import json
import os
from queue import Empty, Queue
from typing import Any, Callable, Optional

from PIL import Image

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest,
    LLMInvocationRequest,
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    STTInvocationRequest,
    TTSInvocationRequest,
    TransportKind,
)

DEFAULT_PROVIDER = "local"
ProgressCallback = Callable[[dict[str, Any]], None]
LLMRequestFactory = Callable[[LLMInvocationRequest], Any]
HealthProvider = Callable[[], RuntimeHealthStatus]


def _default_timeout_seconds() -> float:
    """Return the local-fallback runtime timeout in seconds."""
    configured = os.environ.get(
        "AIRUNNER_LOCAL_FALLBACK_TIMEOUT_SECONDS",
        "120",
    )
    try:
        return float(configured)
    except (TypeError, ValueError):
        return 120.0


DEFAULT_TIMEOUT_SECONDS = _default_timeout_seconds()


def _build_signal_mediator() -> Any:
    """Create the default signal mediator lazily."""
    from airunner_services.utils.application.signal_mediator import (
        SignalMediator,
    )
    return SignalMediator()


def _build_llm_service() -> Any:
    """Create the default LLM API service lazily."""
    from airunner_services.api.services.llm_services import LLMAPIService
    return LLMAPIService()


def _build_stt_service() -> Any:
    """Create the default STT API service lazily."""
    from airunner_services.api.services.stt_services import STTAPIService
    return STTAPIService()


def _build_tts_service() -> Any:
    """Create the default TTS API service lazily."""
    from airunner_services.api.services.tts_services import TTSAPIService
    return TTSAPIService()


def _build_art_service() -> Any:
    """Create the default art API service lazily."""
    from airunner_services.api.services.art_services import ARTAPIService
    return ARTAPIService()


def _resolve_art_request_version(metadata: dict[str, Any]) -> str:
    """Return the model version carried by one art invocation."""
    from airunner_services.contract_enums import normalize_art_version
    version = str(metadata.get("version") or "").strip()
    if version:
        return normalize_art_version(version)
    from airunner_services.contract_enums import DEFAULT_ART_VERSION
    return DEFAULT_ART_VERSION.value


def _resolve_art_request_scheduler(metadata: dict[str, Any]) -> str:
    """Return the scheduler carried by one art invocation."""
    scheduler = str(metadata.get("scheduler") or "").strip()
    if scheduler:
        return scheduler
    from airunner_services.settings import AIRUNNER_DEFAULT_SCHEDULER
    return AIRUNNER_DEFAULT_SCHEDULER


def _resolve_art_pipeline_action(metadata: dict[str, Any]) -> str:
    """Return the requested art pipeline action."""
    pipeline_action = str(metadata.get("pipeline") or "").strip()
    if pipeline_action:
        return pipeline_action
    return "txt2img"


def _resolve_art_generator_section(metadata: dict[str, Any]) -> Any:
    """Return the requested generator section for one art job."""
    from airunner_services.contract_enums import GeneratorSection
    pipeline_action = _resolve_art_pipeline_action(metadata)
    try:
        return GeneratorSection(pipeline_action)
    except ValueError:
        return GeneratorSection.TXT2IMG


def _resolve_art_request_strength(metadata: dict[str, Any]) -> float:
    """Return one normalized strength value for image-conditioned jobs."""
    try:
        return float(metadata.get("strength"))
    except (TypeError, ValueError):
        return 0.5


def _decode_art_metadata_image(encoded_image: Any) -> Any:
    """Return one decoded PIL image from art request metadata."""
    if not encoded_image:
        return None
    try:
        image_bytes = base64.b64decode(encoded_image)
        with Image.open(io.BytesIO(image_bytes)) as image:
            return image.convert("RGB")
    except Exception:
        return None


def _resolve_art_request_image(metadata: dict[str, Any]) -> Any:
    """Return one decoded PIL image carried by the art invocation."""
    return _decode_art_metadata_image(metadata.get("image_b64"))


def _resolve_art_request_mask(metadata: dict[str, Any]) -> Any:
    """Return one decoded mask image carried by the art invocation."""
    return _decode_art_metadata_image(metadata.get("mask_b64"))


def _resolve_art_request_outpaint_mask_blur(
    metadata: dict[str, Any],
) -> int:
    """Return the requested outpaint blur radius."""
    try:
        return int(metadata.get("outpaint_mask_blur") or 0)
    except (TypeError, ValueError):
        return 0


def _resolve_art_active_rect(metadata: dict[str, Any]) -> Any:
    """Return one decoded active rectangle for outpaint requests."""
    raw_rect = metadata.get("active_rect")
    if not raw_rect:
        return None
    if isinstance(raw_rect, str):
        try:
            raw_rect = json.loads(raw_rect)
        except ValueError:
            return None
    if not isinstance(raw_rect, dict):
        return None
    try:
        from airunner_services.art.managers.stablediffusion.rect import Rect
        return Rect(
            int(raw_rect.get("x", 0)),
            int(raw_rect.get("y", 0)),
            int(raw_rect.get("width", 0)),
            int(raw_rect.get("height", 0)),
        )
    except Exception:
        return None


def _resolve_art_operation(metadata: dict[str, Any]) -> str:
    """Return the requested art operation."""
    operation = str(metadata.get("operation") or "generate").strip()
    return operation or "generate"


def _build_llm_request(invocation: LLMInvocationRequest) -> Any:
    """Create an LLM request object for the legacy signal path."""
    from airunner_services.llm.llm_request import LLMRequest
    request = LLMRequest()
    request.temperature = invocation.temperature
    if invocation.max_tokens is not None:
        request.max_new_tokens = invocation.max_tokens
    if invocation.model:
        request.model = invocation.model
    return request


def _resolve_model_type(name: str) -> Any:
    """Resolve a model type lazily to avoid eager imports."""
    from airunner_services.contract_enums import ModelType
    return getattr(ModelType, name)


def _model_health_status(model_status: Any) -> RuntimeHealthStatus:
    """Translate application model status into runtime health status."""
    from airunner_services.contract_enums import ModelStatus
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
    """Common helpers for signal-backed local fallback clients."""

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

    def _emit_signal(
        self, code: Any, data: Optional[dict[str, Any]] = None
    ):
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
        from airunner_services.contract_enums import ModelStatus, SignalCode
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
