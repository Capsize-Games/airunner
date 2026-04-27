"""Tests for the reusable lifecycle service."""

from types import SimpleNamespace

from airunner.enums import SignalCode
from airunner.services.lifecycle_service import CoreLifecycleService


class FakeWorkerManager:
    """Minimal worker manager for lifecycle tests."""

    def __init__(self):
        self.llm_generate_worker = SimpleNamespace(model_manager="rag-manager")


class FakeModelLoadBalancer:
    """Minimal load balancer for lifecycle tests."""

    def __init__(self, worker_manager, logger=None, api=None):
        self.worker_manager = worker_manager
        self.logger = logger
        self.api = api

    def get_loaded_models(self):
        return [
            SimpleNamespace(name="LLM"),
            SimpleNamespace(name="STT"),
        ]


class FakeLogger:
    """Quiet logger double used in lifecycle tests."""

    def info(self, *args, **kwargs):
        return None


class FakeSignalSource:
    """Signal source double for lifecycle tests."""

    def __init__(self):
        self.logger = FakeLogger()
        self.runtime_registry = object()
        self.api_server_thread = object()
        self.registered = []

    def register(self, code, handler):
        self.registered.append((code, handler))

    def on_rag_load_documents_signal(self, data=None):
        return data


def test_initialize_attaches_runtime_state_once():
    signal_source = FakeSignalSource()
    calls = []

    def fake_worker_factory(_worker_cls):
        calls.append("worker")
        return FakeWorkerManager()

    service = CoreLifecycleService(
        signal_source=signal_source,
        logger=signal_source.logger,
        worker_factory=fake_worker_factory,
        balancer_class=FakeModelLoadBalancer,
    )

    service.initialize()
    service.initialize()

    assert calls == ["worker"]
    assert signal_source._worker_manager is service.worker_manager
    assert signal_source.model_load_balancer is service.model_load_balancer
    assert signal_source.registered[0][0] == SignalCode.RAG_LOAD_DOCUMENTS
    assert service.get_status()["loaded_models"] == ["LLM", "STT"]