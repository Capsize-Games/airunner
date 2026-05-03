"""Tests for daemon-backed WorkerManager lifecycle translation."""

from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

from airunner.components.application.gui.windows.main.worker_manager import (
    WorkerManager,
)
from airunner.enums import ModelStatus, ModelType, SignalCode


class FakeDaemonClient:
    """Minimal daemon client double for worker manager tests."""

    def __init__(
        self,
        wait_results=None,
        request_errors=None,
        *,
        available=True,
    ):
        self.calls = []
        self.request_kwargs = []
        self.wait_kwargs = []
        self.availability_checks = []
        self.wait_results = wait_results or {}
        self.request_errors = request_errors or {}
        self.available = available

    def is_available(self, *, timeout_seconds=0.2):
        self.availability_checks.append(timeout_seconds)
        return self.available

    def load_runtime(self, runtime_name, **kwargs):
        self.calls.append(("load", runtime_name))
        self.request_kwargs.append(("load", runtime_name, kwargs))
        error = self.request_errors.get(("load", runtime_name))
        if error is not None:
            raise RuntimeError(error)
        return {"status": "ok"}

    def unload_runtime(self, runtime_name, **kwargs):
        self.calls.append(("unload", runtime_name))
        self.request_kwargs.append(("unload", runtime_name, kwargs))
        error = self.request_errors.get(("unload", runtime_name))
        if error is not None:
            raise RuntimeError(error)
        return {"status": "ok"}

    def wait_runtime_ready(self, runtime_name, *, loaded, **kwargs):
        self.calls.append(("wait", runtime_name, loaded))
        self.wait_kwargs.append((runtime_name, loaded, kwargs))
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
    manager._optional_runtime_enabled = lambda _model_type: True
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
    assert client.request_kwargs == [
        (
            "load",
            "stt",
            {
                "deployment_mode": "sidecar",
                "metadata": None,
                "auto_start": False,
                "timeout_seconds": 5.0,
            },
        )
    ]
    assert client.wait_kwargs == [
        (
            "stt",
            True,
            {
                "deployment_mode": "sidecar",
                "auto_start": False,
                "timeout_seconds": 60.0,
            },
        )
    ]
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
    assert client.request_kwargs == [
        (
            "unload",
            "stt",
            {
                "deployment_mode": "sidecar",
                "metadata": None,
                "auto_start": False,
                "timeout_seconds": 2.0,
            },
        )
    ]
    assert client.wait_kwargs == [
        (
            "stt",
            False,
            {
                "deployment_mode": "sidecar",
                "auto_start": False,
                "timeout_seconds": 5.0,
            },
        )
    ]
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
            {"model": ModelType.LLM, "status": ModelStatus.UNLOADED},
        ),
    ]


def test_daemon_client_uses_refreshed_api_reference():
    client = FakeDaemonClient()
    manager, _emitted = _worker_manager(None)
    manager.api = SimpleNamespace(headless=False)
    manager.refresh_api_reference = Mock(
        return_value=SimpleNamespace(daemon_client=client, headless=False)
    )

    assert WorkerManager._daemon_client(manager) is client


def test_get_main_window_prefers_qt_main_window(monkeypatch):
    main_window = object()
    qt_app = SimpleNamespace(main_window=main_window)

    monkeypatch.setattr(
        "PySide6.QtWidgets.QApplication.instance",
        lambda: qt_app,
    )

    manager, _emitted = _worker_manager(None)

    assert WorkerManager._get_main_window(manager) is main_window


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

    with patch.object(
        WorkerManager,
        "application_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(tts_enabled=False),
    ):
        WorkerManager.on_application_main_window_loaded_signal(manager, {})

    assert calls == [True]


def test_main_window_loaded_starts_enabled_tts_when_daemon_available():
    client = FakeDaemonClient(available=True)
    manager, _emitted = _worker_manager(client)
    calls = []

    manager._start_art_runtime_prewarm = lambda: calls.append("art")
    manager.on_enable_tts_signal = lambda data: calls.append(("tts", data))

    with patch.object(
        WorkerManager,
        "application_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(tts_enabled=True),
    ):
        WorkerManager.on_application_main_window_loaded_signal(manager, {})

    assert calls == ["art", ("tts", {"source": "startup"})]
    assert client.availability_checks == [0.2]


def test_main_window_loaded_defers_enabled_tts_until_daemon_available():
    client = FakeDaemonClient(available=False)
    manager, _emitted = _worker_manager(client)
    calls = []

    manager._start_art_runtime_prewarm = lambda: calls.append("art")
    manager.on_enable_tts_signal = lambda data: calls.append(("tts", data))

    with patch.object(
        WorkerManager,
        "application_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(tts_enabled=True),
    ):
        WorkerManager.on_application_main_window_loaded_signal(manager, {})

    assert calls == ["art"]
    assert client.availability_checks == [0.2]


def test_tts_load_signal_passes_active_voice_metadata():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ), patch.object(
        WorkerManager,
        "chatbot_voice_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(model_type="openvoice"),
    ), patch.object(
        WorkerManager,
        "path_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(tts_model_path="/tmp/openvoice"),
    ):
        WorkerManager.on_enable_tts_signal(manager, {})

    assert FakeThread.started == [True]
    assert client.calls == [("load", "tts"), ("wait", "tts", True)]
    assert client.request_kwargs == [
        (
            "load",
            "tts",
            {
                "deployment_mode": "sidecar",
                "metadata": {
                    "model_type": "openvoice",
                    "model_path": "/tmp/openvoice",
                },
                "auto_start": False,
                "timeout_seconds": 5.0,
            },
        )
    ]
    assert client.wait_kwargs == [
        (
            "tts",
            True,
            {
                "deployment_mode": "sidecar",
                "auto_start": False,
                "timeout_seconds": 90.0,
            },
        )
    ]
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
    assert client.request_kwargs[0][0:2] == ("load", "tts")
    assert client.request_kwargs[0][2]["deployment_mode"] == "sidecar"
    assert client.request_kwargs[0][2]["auto_start"] is False
    assert client.request_kwargs[0][2]["timeout_seconds"] == 5.0
    assert isinstance(client.request_kwargs[0][2]["metadata"], dict)
    assert client.wait_kwargs == [
        (
            "tts",
            True,
            {
                "deployment_mode": "sidecar",
                "auto_start": False,
                "timeout_seconds": 90.0,
            },
        )
    ]
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
    assert client.request_kwargs == [
        (
            "unload",
            "tts",
            {
                "deployment_mode": "sidecar",
                "metadata": None,
                "auto_start": False,
                "timeout_seconds": 2.0,
            },
        )
    ]
    assert client.wait_kwargs == [
        (
            "tts",
            False,
            {
                "deployment_mode": "sidecar",
                "auto_start": False,
                "timeout_seconds": 5.0,
            },
        )
    ]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.TTS, "status": ModelStatus.UNLOADED},
        )
    ]


def test_tts_disable_signal_interrupts_existing_workers_immediately():
    client = FakeDaemonClient()
    manager, _emitted = _worker_manager(client)
    manager._tts_generator_worker = SimpleNamespace(
        add_to_queue=Mock(),
    )
    manager._tts_vocalizer_worker = SimpleNamespace(
        add_to_queue=Mock(),
    )

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_disable_tts_signal(manager, {})

    manager._tts_generator_worker.add_to_queue.assert_any_call(
        {
            "_message_type": "interrupt",
            "data": {},
            "options": {"empty_queue": True},
        }
    )
    manager._tts_vocalizer_worker.add_to_queue.assert_called_once_with(
        {
            "_message_type": "interrupt",
            "data": {},
            "options": {"empty_queue": True},
        }
    )


def test_optional_runtime_unload_timeout_keeps_stt_disabled():
    client = FakeDaemonClient(wait_results={("stt", False): False})
    manager, emitted = _worker_manager(client)

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_stt_unload_signal(manager, {})

    assert emitted == [
        (SignalCode.STT_STOP_CAPTURE_SIGNAL, {}),
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.STT, "status": ModelStatus.UNLOADED},
        ),
    ]


def test_optional_runtime_unload_timeout_keeps_tts_disabled():
    client = FakeDaemonClient(wait_results={("tts", False): False})
    manager, emitted = _worker_manager(client)

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_disable_tts_signal(manager, {})

    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.TTS, "status": ModelStatus.UNLOADED},
        ),
    ]


def test_llm_request_signal_forwards_directly_to_llm_worker():
    manager, _emitted = _worker_manager(FakeDaemonClient())
    direct_worker = SimpleNamespace(on_llm_request_signal=Mock())
    manager._llm_generate_worker = direct_worker
    manager.add_to_queue = Mock()
    manager.logger = SimpleNamespace(info=lambda *args, **kwargs: None)

    WorkerManager.on_llm_request_signal(
        manager,
        {
            "request_data": {"action": None},
            "request_id": "req-123",
        },
    )

    direct_worker.on_llm_request_signal.assert_called_once_with(
        {
            "request_data": {"action": None},
            "request_id": "req-123",
        }
    )
    manager.add_to_queue.assert_not_called()


def test_optional_runtime_load_timeout_recovers_via_status_polling():
    client = FakeDaemonClient(
        request_errors={
            ("load", "stt"): (
                "HTTPConnectionPool(host='127.0.0.1', port=8188): "
                "Read timed out. (read timeout=5.0)"
            )
        }
    )
    manager, emitted = _worker_manager(client)
    manager.logger = SimpleNamespace(debug=Mock(), warning=Mock())

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_stt_load_signal(manager, {})

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
    manager.logger.warning.assert_not_called()


def test_optional_runtime_unload_timeout_recovers_via_status_polling():
    client = FakeDaemonClient(
        request_errors={
            ("unload", "tts"): (
                "HTTPConnectionPool(host='127.0.0.1', port=8188): "
                "Read timed out. (read timeout=2.0)"
            )
        }
    )
    manager, emitted = _worker_manager(client)
    manager.logger = SimpleNamespace(debug=Mock(), warning=Mock())

    FakeThread.started = []
    with patch(
        "airunner.components.application.gui.windows.main.worker_manager.threading.Thread",
        FakeThread,
    ):
        WorkerManager.on_disable_tts_signal(manager, {})

    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.TTS, "status": ModelStatus.UNLOADED},
        ),
    ]
    manager.logger.warning.assert_not_called()


def test_optional_runtime_load_unloads_when_preference_changed():
    client = FakeDaemonClient(
        wait_results={
            ("tts", True): True,
            ("tts", False): True,
        }
    )
    manager, emitted = _worker_manager(client)
    after_success = Mock()
    manager._optional_runtime_enabled = (
        lambda model_type: model_type is not ModelType.TTS
    )

    WorkerManager._control_daemon_runtime(
        manager,
        "tts",
        "load",
        ModelType.TTS,
        after_success=after_success,
    )

    assert client.calls == [
        ("load", "tts"),
        ("wait", "tts", True),
        ("unload", "tts"),
        ("wait", "tts", False),
    ]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.TTS, "status": ModelStatus.LOADING},
        ),
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.TTS, "status": ModelStatus.UNLOADED},
        ),
    ]
    after_success.assert_not_called()


def test_llm_unload_signal_queues_local_worker_request():
    client = None
    manager, _emitted = _worker_manager(client)
    manager._llm_generate_worker = FakeQueuedWorker()

    WorkerManager.on_llm_on_unload_signal(manager, {"source": "ui"})

    assert manager._llm_generate_worker.messages == [
        {"_message_type": "llm_unload", "data": {"source": "ui"}}
    ]


def test_llm_model_changed_signal_is_ui_only_by_default():
    client = FakeDaemonClient()
    manager, _emitted = _worker_manager(client)
    manager._llm_generate_worker = SimpleNamespace(
        on_llm_model_changed_signal=Mock()
    )

    WorkerManager.on_llm_model_changed_signal(
        manager,
        {"model_path": "/tmp/model", "model_name": "Model"},
    )

    assert client.calls == []
    manager._llm_generate_worker.on_llm_model_changed_signal.assert_not_called()


def test_llm_model_changed_signal_unloads_daemon_when_requested():
    client = FakeDaemonClient()
    manager, emitted = _worker_manager(client)
    manager._llm_generate_worker = SimpleNamespace(
        on_llm_model_changed_signal=Mock()
    )

    WorkerManager.on_llm_model_changed_signal(
        manager,
        {"reload_runtime": True},
    )

    assert client.calls == [("unload", "llm"), ("wait", "llm", False)]
    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": ModelStatus.UNLOADED},
        ),
    ]
    manager._llm_generate_worker.on_llm_model_changed_signal.assert_not_called()


def test_llm_model_changed_signal_unloads_local_worker_when_requested():
    client = None
    manager, _emitted = _worker_manager(client)
    manager._llm_generate_worker = SimpleNamespace(
        on_llm_model_changed_signal=Mock()
    )

    WorkerManager.on_llm_model_changed_signal(
        manager,
        {"reload_runtime": True, "model_name": "Model"},
    )

    manager._llm_generate_worker.on_llm_model_changed_signal.assert_called_once_with(
        {"reload_runtime": True, "model_name": "Model"}
    )


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
        {
            "_message_type": "interrupt",
            "data": {},
            "options": {"empty_queue": True},
        },
        {"_message_type": "tts_disable", "data": {"source": "ui"}},
    ]


def test_llm_thinking_signal_forwards_to_tts_generator_worker():
    client = None
    manager, _emitted = _worker_manager(client)
    manager._tts_generator_worker = SimpleNamespace(
        on_llm_thinking_signal=Mock()
    )

    WorkerManager.on_llm_thinking_signal(
        manager,
        {"status": "started", "request_id": "req-1"},
    )

    manager._tts_generator_worker.on_llm_thinking_signal.assert_called_once_with(
        {"status": "started", "request_id": "req-1"}
    )


def test_llm_load_failure_keeps_loaded_local_status():
    client = FakeDaemonClient(
        request_errors={
            ("load", "llm"): (
                "HTTPConnectionPool(host='127.0.0.1', port=8188): "
                "Read timed out. (read timeout=5.0)"
            )
        }
    )
    manager, emitted = _worker_manager(client)
    manager.logger = SimpleNamespace(debug=Mock(), warning=Mock())
    manager._llm_generate_worker = SimpleNamespace(
        current_model_status=lambda: ModelStatus.LOADED,
    )

    WorkerManager.on_llm_load_model_signal(manager, {})

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
    manager.logger.warning.assert_not_called()


def test_llm_unload_failure_keeps_loaded_local_status():
    client = FakeDaemonClient(
        request_errors={
            ("unload", "llm"): (
                "HTTPConnectionPool(host='127.0.0.1', port=8188): "
                "Read timed out. (read timeout=2.0)"
            )
        }
    )
    manager, emitted = _worker_manager(client)
    manager.logger = SimpleNamespace(debug=Mock(), warning=Mock())
    manager._llm_generate_worker = SimpleNamespace(
        current_model_status=lambda: ModelStatus.LOADED,
    )

    WorkerManager.on_llm_on_unload_signal(manager, {"source": "ui"})

    assert emitted == [
        (
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": ModelStatus.LOADED},
        ),
    ]
    manager.logger.warning.assert_not_called()