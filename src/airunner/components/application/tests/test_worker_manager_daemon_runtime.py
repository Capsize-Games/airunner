"""Tests for daemon-backed WorkerManager lifecycle translation."""

from types import SimpleNamespace
from unittest.mock import patch

from airunner.components.application.gui.windows.main.worker_manager import (
    WorkerManager,
)
from airunner.enums import ModelStatus, ModelType, SignalCode


class FakeDaemonClient:
    """Minimal daemon client double for worker manager tests."""

    def __init__(self, wait_results=None):
        self.calls = []
        self.wait_results = wait_results or {}

    def load_runtime(self, runtime_name, **kwargs):
        self.calls.append(("load", runtime_name))
        return {"status": "ok"}

    def unload_runtime(self, runtime_name, **kwargs):
        self.calls.append(("unload", runtime_name))
        return {"status": "ok"}

    def wait_runtime_ready(self, runtime_name, *, loaded, **kwargs):
        self.calls.append(("wait", runtime_name, loaded))
        return self.wait_results.get((runtime_name, loaded), True)


def _worker_manager(client):
    manager = WorkerManager.__new__(WorkerManager)
    manager.api = SimpleNamespace(daemon_client=client, headless=False)
    manager.logger = None
    manager._llm_generate_worker = None
    manager._stt_audio_processor_worker = None
    manager._sd_worker = None
    manager._tts_generator_worker = None
    manager._art_runtime_prewarm_started = False
    emitted = []
    manager.emit_signal = lambda code, data=None: emitted.append((code, data))
    return manager, emitted


class FakeThread:
    """Run background daemon-runtime tasks inline for deterministic tests."""

    started = []

    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self.__class__.started.append(daemon)

    def start(self):
        self._target(*self._args, **self._kwargs)


class FakeQueuedWorker:
    """Minimal worker double that records queued requests."""

    def __init__(self):
        self.messages = []

    def add_to_queue(self, message):
        self.messages.append(message)


def test_llm_load_signal_uses_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    WorkerManager.on_llm_load_model_signal(manager, {})

    assert client.calls == [("load", "llm"), ("wait", "llm", True)]
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

    assert client.calls == [("unload", "art"), ("wait", "art", False)]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.SD, "status": ModelStatus.UNLOADED},
        )
    ]


def test_stt_load_signal_uses_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_stt_load_signal(manager, {})

    assert FakeThread.started == [True]
    assert client.calls == [("load", "stt"), ("wait", "stt", True)]
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

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_stt_unload_signal(manager, {})

    assert FakeThread.started == [True]
    assert client.calls == [("unload", "stt"), ("wait", "stt", False)]
    assert emitted == [
        (SignalCode.STT_STOP_CAPTURE_SIGNAL, {}),
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.STT, "status": ModelStatus.UNLOADED},
        )
    ]


def test_llm_load_signal_marks_failed_when_runtime_never_ready():
    client = FakeDaemonClient(wait_results={("llm", True): False})
    manager, emitted = _worker_manager(client)

    WorkerManager.on_llm_load_model_signal(manager, {})

    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": ModelStatus.LOADING},
        ),
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": ModelStatus.FAILED},
        ),
    ]


def test_prewarm_art_runtime_uses_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)
    manager.logger = SimpleNamespace(debug=lambda *args, **kwargs: None)

    WorkerManager._prewarm_art_runtime(manager)

    assert client.calls == [("load", "art"), ("wait", "art", True)]
    assert emitted == []


def test_main_window_loaded_starts_art_prewarm():
    client = FakeDaemonClient()
    manager, _emitted = _worker_manager(client)
    calls = []
    manager._start_art_runtime_prewarm = lambda: calls.append(True)

    WorkerManager.on_application_main_window_loaded_signal(manager, {})

    assert calls == [True]


def test_tts_enable_signal_uses_background_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_enable_tts_signal(manager, {})

    assert FakeThread.started == [True]
    assert client.calls == [("load", "tts"), ("wait", "tts", True)]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.TTS, "status": ModelStatus.LOADING},
        ),
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.TTS, "status": ModelStatus.LOADED},
        ),
    ]


def test_tts_disable_signal_uses_background_daemon_runtime():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_disable_tts_signal(manager, {})

    assert FakeThread.started == [True]
    assert client.calls == [("unload", "tts"), ("wait", "tts", False)]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.TTS, "status": ModelStatus.UNLOADED},
        )
    ]


def test_llm_unload_signal_queues_local_worker_request():
    client = None
    manager, _emitted = _worker_manager(client)
    manager._llm_generate_worker = FakeQueuedWorker()

    WorkerManager.on_llm_on_unload_signal(manager, {"source": "ui"})

    assert manager._llm_generate_worker.messages == [
        {"_message_type": "llm_unload", "data": {"source": "ui"}}
    ]


def test_stt_unload_signal_queues_local_worker_request():
    client = None
    manager, _emitted = _worker_manager(client)
    manager._stt_audio_processor_worker = FakeQueuedWorker()

    WorkerManager.on_stt_unload_signal(manager, {"source": "ui"})

    assert manager._stt_audio_processor_worker.messages == [
        {"_message_type": "stt_unload", "data": {"source": "ui"}}
    ]


def test_tts_disable_signal_queues_local_worker_request():
    client = None
    manager, _emitted = _worker_manager(client)
    manager._tts_generator_worker = FakeQueuedWorker()

    WorkerManager.on_disable_tts_signal(manager, {"source": "ui"})

    assert manager._tts_generator_worker.messages == [
        {"_message_type": "tts_disable", "data": {"source": "ui"}}
    ]