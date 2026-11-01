"""Local fallback health names the model it actually loaded.

Served-model metadata comes only from real loaded state --
never configuration -- and observed unload/failure clears
it. Hermetic: fake mediator and LLM service.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

import pytest

from airunner_common.contract_enums import (
    ModelStatus,
    ModelType,
    SignalCode,
)
from airunner_services.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
)
from airunner_services.llm.local_capability import (
    build_local_capability,
    proven_loaded_model_id,
)
from airunner_services.runtimes.contracts import (
    RuntimeAction,
    RuntimeHealthStatus,
    RuntimeKind,
)
from airunner_services.runtimes.local_fallback import (
    LocalFallbackLLMClient,
)
from airunner_services.runtimes.registry import (
    RuntimeRegistry,
    RuntimeRoute,
)

_MODEL_PATH = "/models/Qwen/Qwen3.5-9B-Q8_0.gguf"
_MODEL_ID = "qwen3.5-9b"
_OTHER_PATH = "/models/gpt-oss-20b-F16.gguf"


class _FakeMediator:
    """In-memory mediator dispatching to registered handlers."""

    def __init__(self) -> None:
        self.handlers: Dict[Any, List[Callable[..., None]]] = {}

    def register(self, signal: Any, handler: Callable) -> None:
        self.handlers.setdefault(signal, []).append(handler)

    def unregister(self, signal: Any, handler: Callable) -> None:
        registered = self.handlers.get(signal, [])
        if handler in registered:
            registered.remove(handler)

    def dispatch(self, signal: Any, data: Dict[str, Any]) -> None:
        for handler in list(self.handlers.get(signal, [])):
            handler(data)

    def emit_signal(self, signal: Any, data: Dict[str, Any]) -> None:
        self.dispatch(signal, data)


class _FakeLLMService:
    """LLM service whose worker loads/unloads via status signals."""

    def __init__(
        self,
        mediator: _FakeMediator,
        loaded_path: Optional[str] = _MODEL_PATH,
    ) -> None:
        self._mediator = mediator
        self._loaded_path = loaded_path
        self.model_manager = SimpleNamespace(_current_model_path=None)
        worker = SimpleNamespace(_model_manager=self.model_manager)
        self._worker_manager = SimpleNamespace(_llm_generate_worker=worker)

    def emit_signal(self, code: Any, data: Any = None) -> None:
        del data
        if code is SignalCode.LLM_LOAD_SIGNAL:
            self._apply(self._loaded_path, ModelStatus.LOADED)
        elif code is SignalCode.LLM_UNLOAD_SIGNAL:
            self._apply(None, ModelStatus.UNLOADED)

    def simulate_external(self, status: ModelStatus) -> None:
        """Apply an out-of-band unload/crash status event."""
        self._apply(None, status)

    def _apply(self, path: Optional[str], status: ModelStatus) -> None:
        self.model_manager._current_model_path = path
        self._mediator.dispatch(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": status},
        )


def _client(
    mediator: _FakeMediator,
    service: _FakeLLMService,
    **kwargs: Any,
) -> LocalFallbackLLMClient:
    return LocalFallbackLLMClient(
        llm_service=service, mediator=mediator, timeout_seconds=5.0, **kwargs
    )


def _setup(**service_kwargs: Any) -> tuple[Any, Any, Any]:
    mediator = _FakeMediator()
    service = _FakeLLMService(mediator, **service_kwargs)
    return mediator, service, _client(mediator, service)


def _envelope(action: RuntimeAction, request_id: str) -> Any:
    return RequestEnvelope(
        runtime=RuntimeKind.LLM,
        action=action,
        payload={},
        request_id=request_id,
    )


def _registry(client: LocalFallbackLLMClient) -> RuntimeRegistry:
    registry = RuntimeRegistry()
    route = RuntimeRoute(RuntimeKind.LLM, provider=client.descriptor.provider)
    registry.register(route, client)
    return registry


def _loaded_ids(client: LocalFallbackLLMClient) -> List[str]:
    payload = build_local_capability(
        registry=_registry(client), configured_model_id="gpt-oss-20b"
    )
    return [m["id"] for m in payload["models"] if m["loaded"]]


def _proven_id(client: LocalFallbackLLMClient) -> str:
    return proven_loaded_model_id(_registry(client), "gpt-oss-20b")


def _load(client: LocalFallbackLLMClient) -> Any:
    return client.invoke(_envelope(RuntimeAction.LOAD_MODEL, "load-1"))


def test_fallback_ready_metadata_reports_loaded_model() -> None:
    """READY health names the worker's actually loaded model."""
    _mediator, _service, client = _setup()
    response = _load(client)
    assert response.status is EnvelopeStatus.SUCCEEDED
    assert response.metadata["model_status"] == "Loaded"
    assert response.metadata["model_id"] == _MODEL_ID
    assert response.metadata["model_path"] == _MODEL_PATH
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_id"] == _MODEL_ID
    assert health.metadata["model_path"] == _MODEL_PATH
    assert _loaded_ids(client) == [_MODEL_ID]
    assert _proven_id(client) == _MODEL_ID
    client.close()


def test_fallback_unload_clears_loaded_model() -> None:
    """After unload, health and capability claim no model."""
    _mediator, _service, client = _setup()
    _load(client)
    response = client.invoke(_envelope(RuntimeAction.UNLOAD_MODEL, "unload-1"))
    assert response.status is EnvelopeStatus.SUCCEEDED
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.STOPPED
    assert "model_id" not in health.metadata
    assert "model_path" not in health.metadata
    assert _loaded_ids(client) == []
    assert _proven_id(client) == ""
    client.close()


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ModelStatus.UNLOADED, RuntimeHealthStatus.STOPPED),
        (ModelStatus.FAILED, RuntimeHealthStatus.FAILED),
    ],
)
def test_external_unload_or_failure_clears_loaded_model(
    status: ModelStatus, expected: RuntimeHealthStatus
) -> None:
    """Out-of-band unload/crash leaves no stale READY claim."""
    _mediator, service, client = _setup()
    _load(client)
    service.simulate_external(status)
    health = client.healthcheck()
    assert health.status is expected
    assert "model_id" not in health.metadata
    assert "model_path" not in health.metadata
    assert _loaded_ids(client) == []
    client.close()


def test_ready_without_worker_identity_claims_no_model() -> None:
    """READY with no loaded path proves no served model."""
    _mediator, _service, client = _setup(loaded_path=None)
    _load(client)
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata == {"model_status": "Loaded"}
    assert _loaded_ids(client) == []
    client.close()


def test_status_event_identity_is_used_when_named() -> None:
    """A status event naming its model path is real loaded state."""
    mediator, service, client = _setup(loaded_path=None)
    service._worker_manager = None  # unreachable: event stands
    mediator.dispatch(
        SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
        {
            "model": ModelType.LLM,
            "status": ModelStatus.LOADED,
            "model_path": _MODEL_PATH,
        },
    )
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_path"] == _MODEL_PATH
    assert _loaded_ids(client) == [_MODEL_ID]
    client.close()


def test_loaded_identity_is_snapshot_not_live_configuration() -> None:
    """Identity is frozen at load; later config changes do not leak."""
    mediator = _FakeMediator()
    service = _FakeLLMService(mediator, loaded_path=None)
    state: Dict[str, Any] = {"model_path": _MODEL_PATH}
    client = _client(
        mediator, service, loaded_model_provider=lambda: dict(state)
    )
    _load(client)
    state["model_path"] = _OTHER_PATH
    health = client.healthcheck()
    assert health.metadata["model_path"] == _MODEL_PATH
    service.simulate_external(ModelStatus.UNLOADED)
    health = client.healthcheck()
    assert "model_path" not in health.metadata
    assert "model_id" not in health.metadata
    client.close()
