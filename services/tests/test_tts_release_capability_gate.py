"""Release TTS capability gates do not import or start OpenVoice."""

from __future__ import annotations

import builtins
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


def test_worker_rejects_openvoice_before_importing_its_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from airunner_services.runtimes.openvoice_exceptions import OpenVoiceError
    from airunner_services.workers.tts_generator_worker import (
        TTSGeneratorWorker,
    )

    worker = TTSGeneratorWorker.__new__(TTSGeneratorWorker)
    worker.logger = SimpleNamespace(
        info=Mock(), debug=Mock(), warning=Mock(), error=Mock()
    )
    worker.tts = None
    worker._current_model = None
    monkeypatch.setattr(worker, "_active_tts_model", lambda: "OpenVoice")
    real_import = builtins.__import__

    def reject_vendor_import(name, *args, **kwargs):
        if name.startswith("airunner_tts_vendor.openvoice") or name == (
            "airunner_services.runtimes.openvoice_model_manager"
        ):
            raise AssertionError("deferred OpenVoice import attempted")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_vendor_import)

    with pytest.raises(OpenVoiceError, match="unavailable in this release"):
        worker._initialize_tts_model_manager()

    assert worker.tts is None
    assert worker._current_model is None


def test_worker_keeps_espeak_manager_selection(monkeypatch) -> None:
    from airunner_services.workers.tts_generator_worker import (
        TTSGeneratorWorker,
    )

    created = []

    class FakeEspeakManager:
        def __init__(self) -> None:
            created.append(self)

    module = ModuleType(
        "airunner_services.runtimes.espeak_model_manager"
    )
    module.EspeakModelManager = FakeEspeakManager
    monkeypatch.setitem(
        sys.modules,
        "airunner_services.runtimes.espeak_model_manager",
        module,
    )
    worker = TTSGeneratorWorker.__new__(TTSGeneratorWorker)
    worker.logger = SimpleNamespace(info=Mock(), debug=Mock())
    worker.tts = None
    worker._current_model = None
    monkeypatch.setattr(worker, "_active_tts_model", lambda: "Espeak")

    worker._initialize_tts_model_manager()

    assert len(created) == 1
    assert worker.tts is created[0]


def _settings(model_type: str | None):
    from airunner_services.runtimes.tts_daemon_runtime_settings import (
        TTSDaemonRuntimeSettings,
    )

    return TTSDaemonRuntimeSettings(
        host="127.0.0.1",
        port=8191,
        base_daemon_config_path=None,
        tts_model_path=None,
        tts_model_type=model_type,
        startup_timeout_seconds=1.0,
        request_timeout_seconds=1.0,
    )


class _FakeLauncher:
    endpoint = "http://127.0.0.1:8191"
    api_base_url = endpoint + "/api/v1/tts"

    def __init__(self) -> None:
        self.start_calls = 0
        self.health_calls = 0

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        return None

    def is_running(self) -> bool:
        return self.start_calls > 0

    def is_ready(self) -> bool:
        return False

    def health_status(self):
        self.health_calls += 1
        from airunner_services.runtimes.contracts import RuntimeHealthStatus

        return RuntimeHealthStatus.READY, "ready"


def test_sidecar_refuses_openvoice_without_starting_child() -> None:
    from airunner_services.ipc.messages import RequestEnvelope, EnvelopeStatus
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
    from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient
    from airunner_services.runtimes.contracts import RuntimeHealthStatus

    launcher = _FakeLauncher()
    runtime = SidecarTTSClient(
        settings=_settings("OpenVoice"),
        launcher=launcher,
    )
    runtime._request = Mock(side_effect=AssertionError("request attempted"))
    load_result = runtime.invoke(
        RequestEnvelope(
            request_id="load-openvoice",
            runtime=RuntimeKind.TTS,
            action=RuntimeAction.LOAD_MODEL,
            metadata={},
        )
    )
    synthesize_result = runtime.invoke(
        RequestEnvelope(
            request_id="synthesize-openvoice",
            runtime=RuntimeKind.TTS,
            action=RuntimeAction.INVOKE,
            payload={
                "text": "Hello",
                "metadata": {"model_type": "OpenVoice"},
            },
        )
    )
    health = runtime.healthcheck()

    assert load_result.status is EnvelopeStatus.FAILED
    assert load_result.error.code == "tts_backend_unavailable"
    assert synthesize_result.status is EnvelopeStatus.FAILED
    assert synthesize_result.error.code == "tts_backend_unavailable"
    assert health.status is RuntimeHealthStatus.FAILED
    assert health.metadata["capability_status"] == "deferred"
    assert launcher.start_calls == 0
    assert launcher.health_calls == 0
    runtime._request.assert_not_called()


def test_sidecar_espeak_load_path_still_uses_launcher() -> None:
    from airunner_services.ipc.messages import RequestEnvelope, EnvelopeStatus
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
    from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient

    launcher = _FakeLauncher()
    runtime = SidecarTTSClient(settings=_settings(None), launcher=launcher)
    requests = []
    runtime._request = lambda *args, **kwargs: requests.append((args, kwargs))

    result = runtime.invoke(
        RequestEnvelope(
            request_id="load-espeak",
            runtime=RuntimeKind.TTS,
            action=RuntimeAction.LOAD_MODEL,
            metadata={"model_type": "Espeak"},
        )
    )

    assert result.status is EnvelopeStatus.SUCCEEDED
    assert launcher.start_calls == 1
    assert len(requests) == 1


def test_local_fallback_environment_cannot_start_openvoice_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from airunner_services.ipc.messages import RequestEnvelope, EnvelopeStatus
    from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
    from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient

    class LazyWorkerManager:
        access_count = 0

        @property
        def tts_generator_worker(self):
            self.access_count += 1
            raise AssertionError("deferred backend must not create a worker")

    worker_manager = LazyWorkerManager()
    runtime = LocalFallbackTTSClient(
        signal_source=SimpleNamespace(_worker_manager=worker_manager),
        mediator=SimpleNamespace(),
    )
    monkeypatch.setenv("AIRUNNER_TTS_MODEL_TYPE", "OpenVoice")

    result = runtime.invoke(
        RequestEnvelope(
            request_id="invoke-openvoice-env",
            runtime=RuntimeKind.TTS,
            action=RuntimeAction.INVOKE,
            payload={"text": "Hello"},
        )
    )

    assert result.status is EnvelopeStatus.FAILED
    assert result.error.code == "tts_backend_unavailable"
    assert worker_manager.access_count == 0
