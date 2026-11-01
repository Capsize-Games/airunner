"""Silent in-process unloads are observable at healthcheck.

A loaded-model snapshot is re-validated against live worker
state: a reachable worker reporting no (or a different)
current model overrides the snapshot, while an unreachable
worker chain never erases event-reported identity.
Hermetic: fake mediator and LLM service.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, Dict, List

from airunner_common.contract_enums import (
    ModelStatus,
    ModelType,
    SignalCode,
)
from airunner_services.ipc.messages import RequestEnvelope
from airunner_services.llm.local_capability import (
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
_OTHER_ID = "gpt-oss-20b"


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
    """LLM service whose worker state tests can move silently."""

    def __init__(self, mediator: _FakeMediator) -> None:
        self._mediator = mediator
        self.model_manager = SimpleNamespace(_current_model_path=None)
        self.worker = SimpleNamespace(_model_manager=self.model_manager)
        self._worker_manager: Any = SimpleNamespace(
            _llm_generate_worker=self.worker
        )

    def emit_signal(self, code: Any, data: Any = None) -> None:
        del data
        if code is SignalCode.LLM_LOAD_SIGNAL:
            self.model_manager._current_model_path = _MODEL_PATH
            self._mediator.dispatch(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {"model": ModelType.LLM, "status": ModelStatus.LOADED},
            )

    def silent_unload(self) -> None:
        """Drop the model without any status signal."""
        self.model_manager._current_model_path = None

    def silent_switch(self) -> None:
        """Swap the loaded model without any status signal."""
        self.model_manager._current_model_path = _OTHER_PATH


def _setup(**kwargs: Any) -> tuple[Any, Any]:
    mediator = _FakeMediator()
    service = _FakeLLMService(mediator)
    client = LocalFallbackLLMClient(
        llm_service=service,
        mediator=mediator,
        timeout_seconds=5.0,
        **kwargs,
    )
    return service, client


def _load(client: LocalFallbackLLMClient) -> Any:
    return client.invoke(
        RequestEnvelope(
            runtime=RuntimeKind.LLM,
            action=RuntimeAction.LOAD_MODEL,
            payload={},
            request_id="load-1",
        )
    )


def _proven_id(client: LocalFallbackLLMClient) -> str:
    registry = RuntimeRegistry()
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=client.descriptor.provider),
        client,
    )
    return proven_loaded_model_id(registry, "gpt-oss-20b")


def test_silent_unload_clears_identity_and_stops_health() -> None:
    """A reachable worker with no model ends the READY claim."""
    service, client = _setup()
    _load(client)
    assert client.healthcheck().metadata["model_id"] == _MODEL_ID
    service.silent_unload()
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.STOPPED
    assert health.metadata == {"model_status": "Unloaded"}
    assert _proven_id(client) == ""
    client.close()


def test_silent_switch_updates_identity() -> None:
    """A reachable worker naming another model is believed."""
    service, client = _setup()
    _load(client)
    service.silent_switch()
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_id"] == _OTHER_ID
    assert health.metadata["model_path"] == _OTHER_PATH
    assert _proven_id(client) == _OTHER_ID
    client.close()


def test_unreachable_worker_keeps_snapshot_identity() -> None:
    """No worker chain at all cannot erase a loaded snapshot."""
    service, client = _setup()
    _load(client)
    service._worker_manager = None
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_id"] == _MODEL_ID
    assert health.metadata["model_path"] == _MODEL_PATH
    client.close()


def test_missing_manager_attribute_keeps_snapshot() -> None:
    """A manager without loaded state is unknown, not unloaded."""
    service, client = _setup()
    _load(client)
    service.worker._model_manager = SimpleNamespace()
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_id"] == _MODEL_ID
    client.close()


def test_unreachable_worker_lookup_keeps_snapshot() -> None:
    """A worker lookup that errors is unknown, not unloaded."""
    service, client = _setup()
    _load(client)

    def _boom() -> Any:
        raise RuntimeError("no worker")

    service._worker_manager = _boom
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_id"] == _MODEL_ID
    client.close()


def test_failing_provider_keeps_snapshot_identity() -> None:
    """A probe that errors cannot erase or crash health."""
    state = {"fail": False}

    def _provider() -> Dict[str, Any]:
        if state["fail"]:
            raise RuntimeError("probe down")
        return {"model_path": _MODEL_PATH}

    _service, client = _setup(loaded_model_provider=_provider)
    _load(client)
    state["fail"] = True
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_path"] == _MODEL_PATH
    client.close()


def test_provider_reporting_no_model_clears_identity() -> None:
    """An authoritative probe going empty ends the claim."""
    state: Dict[str, Any] = {"model_path": _MODEL_PATH}
    _service, client = _setup(loaded_model_provider=lambda: dict(state))
    _load(client)
    assert client.healthcheck().metadata["model_path"] == _MODEL_PATH
    state.clear()
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.STOPPED
    assert "model_path" not in health.metadata
    assert _proven_id(client) == ""
    client.close()
