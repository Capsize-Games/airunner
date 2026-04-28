"""Tests for daemon-backed WorkerManager lifecycle translation."""

from types import SimpleNamespace

from airunner.components.application.gui.windows.main.worker_manager import (
    WorkerManager,
)
from airunner.enums import ModelStatus, ModelType, SignalCode


class FakeDaemonClient:
    """Minimal daemon client double for worker manager tests."""

    def __init__(self):
        self.calls = []

    def load_runtime(self, runtime_name, **kwargs):
        self.calls.append(("load", runtime_name))
        return {"status": "ok"}

    def unload_runtime(self, runtime_name, **kwargs):
        self.calls.append(("unload", runtime_name))
        return {"status": "ok"}


def _worker_manager(client):
    manager = WorkerManager.__new__(WorkerManager)
    manager.api = SimpleNamespace(daemon_client=client, headless=False)
    manager.logger = None
    manager._llm_generate_worker = None
    manager._stt_audio_processor_worker = None
    manager._sd_worker = None
    manager._tts_generator_worker = None
    emitted = []
    manager.emit_signal = lambda code, data=None: emitted.append((code, data))
    return manager, emitted


def test_llm_load_signal_uses_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    WorkerManager.on_llm_load_model_signal(manager, {})

    assert client.calls == [("load", "llm")]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": ModelStatus.LOADING},
        ),
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": ModelStatus.LOADED},
        ),
    ]


def test_sd_unload_signal_uses_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    WorkerManager.on_unload_art_signal(manager, {})

    assert client.calls == [("unload", "art")]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.SD, "status": ModelStatus.UNLOADED},
        )
    ]


def test_stt_load_signal_uses_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    WorkerManager.on_stt_load_signal(manager, {})

    assert client.calls == [("load", "stt")]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.STT, "status": ModelStatus.LOADING},
        ),
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.STT, "status": ModelStatus.LOADED},
        ),
        (SignalCode.STT_START_CAPTURE_SIGNAL, {}),
    ]


def test_stt_unload_signal_uses_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    WorkerManager.on_stt_unload_signal(manager, {})

    assert client.calls == [("unload", "stt")]
    assert emitted == [
        (SignalCode.STT_STOP_CAPTURE_SIGNAL, {}),
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.STT, "status": ModelStatus.UNLOADED},
        )
    ]