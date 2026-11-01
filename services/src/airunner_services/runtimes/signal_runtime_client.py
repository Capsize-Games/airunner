"""Signal-backed base client for local fallback runtimes."""

from __future__ import annotations

import os
import threading
from queue import Empty, Queue
from typing import Any, Callable, Optional

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)


HealthProvider = Callable[[], RuntimeHealthStatus]
LoadedModelProvider = Callable[[], dict[str, Any]]


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
    from airunner_services.utils.application.signal_mediator import SignalMediator

    return SignalMediator()


def _resolve_model_type(name: str) -> Any:
    """Resolve a model type lazily to avoid eager imports."""
    from airunner_common.contract_enums import ModelType

    return getattr(ModelType, name)


def _model_health_status(model_status: Any) -> RuntimeHealthStatus:
    """Translate application model status into runtime health status."""
    from airunner_common.contract_enums import ModelStatus

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


def _is_loaded_model_status(model_status: Any) -> bool:
    """Return True only for statuses that prove a model is loaded."""
    from airunner_common.contract_enums import ModelStatus

    return model_status in (ModelStatus.LOADED, ModelStatus.READY)


def _served_model_metadata(
    raw: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Keep only non-empty served-model identity fields."""
    if not raw:
        return {}
    metadata: dict[str, Any] = {}
    for key in ("model_id", "model_path"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            metadata[key] = value.strip()
    return metadata


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
        loaded_model_provider: Optional[LoadedModelProvider] = None,
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
        self._signal_lock = threading.Lock()
        self._timeout_seconds = timeout_seconds
        self._health_provider = health_provider
        self._last_model_status = None
        self._model_type = model_type
        self._loaded_model_provider = loaded_model_provider
        self._loaded_model: dict[str, Any] = {}
        self._status_handler = self._on_model_status_changed
        self._status_registered = False
        self._register_status_handler()

    def healthcheck(self) -> RuntimeHealth:
        """Return current health state for the runtime client."""
        if self._health_provider is not None:
            return RuntimeHealth(
                descriptor=self.descriptor,
                status=self._health_provider(),
            )
        metadata = self._status_metadata()
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=_model_health_status(self._last_model_status),
            details=_model_status_value(self._last_model_status),
            metadata=metadata,
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
        if _is_loaded_model_status(self._last_model_status):
            self._revalidate_loaded_model()
        if self._last_model_status is None:
            return {}
        metadata = {
            "model_status": _model_status_value(self._last_model_status)
        }
        metadata.update(self._loaded_model_metadata())
        return metadata

    def _cache_status(
        self,
        model_status: Any,
        event_data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Track status and the model identity it proves loaded."""
        self._last_model_status = model_status
        if not _is_loaded_model_status(model_status):
            self._loaded_model = {}
            return
        self._loaded_model = self._snapshot_loaded_model(event_data)

    def _snapshot_loaded_model(
        self, event_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Snapshot served-model identity at a loaded transition."""
        identity = _served_model_metadata(event_data)
        if identity:
            return identity
        return self._probe_loaded_model()

    def _probe_loaded_model(self) -> dict[str, Any]:
        """Return identity from the configured loaded-state probe."""
        if self._loaded_model_provider is None:
            return {}
        return _served_model_metadata(self._loaded_model_provider())

    def _loaded_model_metadata(self) -> dict[str, Any]:
        """Return loaded identity, probing once if still unknown."""
        if not self._loaded_model and _is_loaded_model_status(
            self._last_model_status
        ):
            self._loaded_model = self._probe_loaded_model()
        return dict(self._loaded_model)

    def _revalidate_loaded_model(self) -> None:
        """Drop a snapshot the loaded-state probe contradicts.

        Only a probe positively reporting no loaded model
        clears the snapshot; without a probe there is no live
        evidence and the snapshot stands.
        """
        if not self._loaded_model:
            return
        if self._loaded_model_provider is None:
            return
        try:
            current = _served_model_metadata(
                self._loaded_model_provider()
            )
        except Exception:
            return
        if not current:
            self._mark_silently_unloaded()

    def _mark_silently_unloaded(self) -> None:
        """Record an unload observed without a status signal."""
        from airunner_common.contract_enums import ModelStatus

        self._loaded_model = {}
        self._last_model_status = ModelStatus.UNLOADED

    def _register_status_handler(self) -> None:
        """Track external load/unload events for this model type."""
        register = getattr(self._mediator, "register", None)
        if not callable(register):
            return
        from airunner_common.contract_enums import SignalCode

        register(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self._status_handler
        )
        self._status_registered = True

    def _on_model_status_changed(self, data: dict[str, Any]) -> None:
        """Cache one external model-status event for this client."""
        if not isinstance(data, dict):
            return
        if not self._matches_model(data.get("model")):
            return
        status = data.get("status")
        if status is not None:
            self._cache_status(status, data)

    def close(self) -> None:
        """Stop tracking external model-status events."""
        if not self._status_registered:
            return
        unregister = getattr(self._mediator, "unregister", None)
        if callable(unregister):
            from airunner_common.contract_enums import SignalCode

            unregister(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                self._status_handler,
            )
        self._status_registered = False

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
        from airunner_common.contract_enums import ModelStatus, SignalCode

        status_queue: Queue[Any] = Queue()

        def on_status_changed(data: dict[str, Any]) -> None:
            model = data.get("model")
            if not self._matches_model(model):
                return
            status = data.get("status")
            self._cache_status(status, data)
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
