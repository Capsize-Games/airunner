"""Tests for the daemon-backed GUI model load balancer."""

from types import SimpleNamespace

from airunner.components.application.gui.windows.main.model_load_balancer import (
    ModelLoadBalancer,
)
from airunner.enums import ModelStatus, ModelType


class FakeDaemonClient:
    """Minimal daemon client double for balancer tests."""

    def __init__(self, loaded_models=None, runtimes=None, wait_results=None):
        self.loaded_models = loaded_models or []
        self.runtimes = runtimes or []
        self.wait_results = wait_results or {}
        self.calls = []

    def daemon_runtime_status(self, *, auto_start=False):
        self.calls.append(("status", auto_start))
        return {
            "lifecycle": {"loaded_models": self.loaded_models},
            "runtimes": self.runtimes,
        }

    def load_runtime(self, runtime_name, **kwargs):
        self.calls.append(("load", runtime_name))
        return {"status": "ok"}

    def unload_runtime(self, runtime_name, **kwargs):
        self.calls.append(("unload", runtime_name))
        return {"status": "ok"}

    def wait_runtime_ready(self, runtime_name, *, loaded, **kwargs):
        self.calls.append(("wait", runtime_name, loaded))
        return self.wait_results.get((runtime_name, loaded), True)


def _balancer(client):
    status_updates = []
    api = SimpleNamespace(
        daemon_client=client,
        headless=False,
        change_model_status=lambda model, status: status_updates.append(
            (model, status)
        ),
    )
    return ModelLoadBalancer(worker_manager=None, api=api), status_updates


def test_get_loaded_models_prefers_daemon_status():
    balancer, _status_updates = _balancer(
        FakeDaemonClient(
            loaded_models=[],
            runtimes=[
                {"runtime": "llm", "loaded": True},
                {"runtime": "art", "loaded": True},
            ],
        )
    )

    loaded_models = balancer.get_loaded_models()

    assert loaded_models == [ModelType.LLM, ModelType.SD]


def test_switch_to_non_art_mode_loads_llm_by_default():
    client = FakeDaemonClient(["SD"])
    balancer, status_updates = _balancer(client)

    balancer.switch_to_non_art_mode()

    assert ("load", "llm") in client.calls
    assert ("wait", "llm", True) in client.calls
    assert status_updates[-1] == (ModelType.LLM, ModelStatus.LOADED)


def test_switch_to_art_mode_unloads_loaded_non_art_models():
    client = FakeDaemonClient(
        loaded_models=[],
        runtimes=[
            {"runtime": "llm", "loaded": True},
            {"runtime": "tts", "loaded": True},
        ],
    )
    balancer, _status_updates = _balancer(client)

    balancer.switch_to_art_mode()

    assert ("unload", "llm") in client.calls
    assert ("unload", "tts") in client.calls
    assert ("wait", "llm", False) in client.calls
    assert ("wait", "tts", False) in client.calls


def test_switch_to_non_art_mode_marks_failed_when_runtime_stays_unready():
    client = FakeDaemonClient(wait_results={("llm", True): False})
    balancer, status_updates = _balancer(client)

    balancer.switch_to_non_art_mode()

    assert status_updates[-1] == (ModelType.LLM, ModelStatus.FAILED)
