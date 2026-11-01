"""Request parameter handling for headless local TTS fallback."""

from __future__ import annotations

from types import SimpleNamespace

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_services.runtimes.contracts import TTSInvocationRequest
from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient
from airunner_services.requests.tts_request import openvoice_speed_multiplier


class _FakeWorker:
    chatbot = SimpleNamespace(gender="Female")

    @staticmethod
    def _active_tts_model() -> str:
        return "OpenVoice"

    @staticmethod
    def _current_tts_status():
        from airunner_common.contract_enums import ModelStatus

        return ModelStatus.LOADED


class _FakeWorkerManager:
    def __init__(self, worker: _FakeWorker) -> None:
        self.tts_generator_worker = worker


class _FakeSignalSource:
    def __init__(self, worker: _FakeWorker) -> None:
        self._worker_manager = _FakeWorkerManager(worker)

    def emit_signal(self, *_args, **_kwargs) -> None:
        pass


def test_headless_openvoice_request_carries_supported_default_voice_and_speed() -> None:
    worker = _FakeWorker()
    client = LocalFallbackTTSClient(signal_source=_FakeSignalSource(worker))
    invocation = TTSInvocationRequest(text="hello", speed=1.75)

    request = client._tts_request(invocation, worker)

    assert request.message == "hello"
    assert request.gender == "Female"
    assert request.voice == "default"
    assert request.speed == 175
    assert openvoice_speed_multiplier(request, default=1.0) == 1.75


def test_headless_openvoice_rejects_unavailable_voice_without_rendering() -> None:
    worker = _FakeWorker()
    client = LocalFallbackTTSClient(signal_source=_FakeSignalSource(worker))
    client._audio_payload = lambda _invocation: (_ for _ in ()).throw(
        AssertionError("unsupported voice must fail before synthesis")
    )

    response = client._invoke_headless_runtime(
        "request-1",
        TTSInvocationRequest(text="hello", voice="voice-x"),
    )

    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "tts_unsupported_parameter"
    assert "voice" in response.error.message


class _WorkerManager:
    def __init__(self, worker=None) -> None:
        self._tts_generator_worker = worker
        self.property_accesses = 0

    @property
    def tts_generator_worker(self):
        self.property_accesses += 1
        raise AssertionError("health must not resolve the lazy worker property")


def test_healthcheck_advertises_default_voice_from_loaded_openvoice_only() -> None:
    worker_manager = _WorkerManager(_FakeWorker())
    client = LocalFallbackTTSClient(
        signal_source=SimpleNamespace(_worker_manager=worker_manager)
    )

    health = client.healthcheck()

    assert health.status.value == "ready"
    assert health.metadata["voice_ids"] == ["default"]
    assert worker_manager.property_accesses == 0


def test_healthcheck_does_not_create_or_advertise_unloaded_worker() -> None:
    worker_manager = _WorkerManager()
    client = LocalFallbackTTSClient(
        signal_source=SimpleNamespace(_worker_manager=worker_manager)
    )

    health = client.healthcheck()

    assert health.metadata.get("voice_ids") is None
    assert worker_manager.property_accesses == 0
