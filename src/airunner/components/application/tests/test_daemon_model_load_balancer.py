"""Tests for the daemon-backed GUI model load balancer."""

from types import SimpleNamespace

from airunner.components.application.gui.windows.main.model_load_balancer import (
    ModelLoadBalancer,
)
from airunner.enums import ModelType


class FakeDaemonClient:
    """Minimal daemon client double for balancer tests."""

    def __init__(self, loaded_models=None):
        self.loaded_models = loaded_models or []
        self.calls = []

    def daemon_runtime_status(self, *, auto_start=False):
        self.calls.append(("status", auto_start))
        return {"lifecycle": {"loaded_models": self.loaded_models}}

    def load_runtime(self, runtime_name, **kwargs):
        self.calls.append(("load", runtime_name))
        return {"status": "ok"}

    def unload_runtime(self, runtime_name, **kwargs):
        self.calls.append(("unload", runtime_name))
        return {"status": "ok"}


def _balancer(client):
    api = SimpleNamespace(daemon_client=client, headless=False)
    return ModelLoadBalancer(worker_manager=None, api=api)


def test_get_loaded_models_prefers_daemon_status():
    balancer = _balancer(FakeDaemonClient(["LLM", "SD"]))

    loaded_models = balancer.get_loaded_models()

    assert loaded_models == [ModelType.LLM, ModelType.SD]


def test_switch_to_non_art_mode_loads_llm_by_default():
    client = FakeDaemonClient(["SD"])
    balancer = _balancer(client)

    balancer.switch_to_non_art_mode()

    assert ("load", "llm") in client.calls


def test_switch_to_art_mode_unloads_loaded_non_art_models():
    client = FakeDaemonClient(["LLM", "TTS"])
    balancer = _balancer(client)

    balancer.switch_to_art_mode()

    assert ("unload", "llm") in client.calls
    assert ("unload", "tts") in client.calls
