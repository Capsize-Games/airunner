"""Tests for the whisper.cpp sidecar runtime client."""

import json

from airunner.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeHealthStatus,
    RuntimeKind,
)
from airunner.runtimes.sidecar_stt_client import (
    SidecarSTTClient,
    register_sidecar_stt_client,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner.runtimes.whisper_cpp_runtime_settings import (
    WhisperCppRuntimeSettings,
)


class FakeResponse:
    """Minimal context-managed HTTP response."""

    def __init__(self, body: bytes = b""):
        self._body = body
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


class FakeLauncher:
    """Minimal launcher double for sidecar client tests."""

    def __init__(self, settings):
        self.settings = settings
        self.endpoint = settings.endpoint
        self.inference_url = (
            f"{settings.endpoint}{settings.request_prefix}"
            f"{settings.normalized_inference_path}"
        )
        self.started = 0
        self.stopped = 0
        self.status = RuntimeHealthStatus.READY
        self.details = "ready"

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def health_status(self):
        return self.status, self.details


def _settings() -> WhisperCppRuntimeSettings:
    return WhisperCppRuntimeSettings(
        executable="whisper-server",
        host="127.0.0.1",
        port=8012,
        model_path="/tmp/ggml-base.en.bin",
        model_id="ggml-base.en.bin",
        n_threads=4,
        n_processors=1,
        language="auto",
        request_path="",
        inference_path="/inference",
        convert_audio=False,
        use_gpu=True,
        startup_timeout_seconds=1.0,
    )


def _request(action: RuntimeAction = RuntimeAction.INVOKE) -> RequestEnvelope:
    return RequestEnvelope(
        request_id="req-1",
        runtime=RuntimeKind.STT,
        action=action,
        payload={
            "audio_b64": "ZmFrZS1hdWRpbw==",
            "mime_type": "audio/wav",
            "language": "en",
        },
    )


def test_load_model_starts_launcher():
    launcher = FakeLauncher(_settings())
    client = SidecarSTTClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=lambda *args, **kwargs: FakeResponse(),
    )

    response = client.invoke(_request(RuntimeAction.LOAD_MODEL))

    assert launcher.started == 1
    assert response.status is EnvelopeStatus.SUCCEEDED


def test_invoke_wraps_transcription_response():
    launcher = FakeLauncher(_settings())
    opened = []

    def fake_opener(request, timeout):
        opened.append(request)
        return FakeResponse(
            body=json.dumps({"text": "hello", "language": "en"}).encode(
                "utf-8"
            )
        )

    client = SidecarSTTClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=fake_opener,
    )

    response = client.invoke(_request())

    assert launcher.started == 1
    assert opened[0].full_url.endswith("/inference")
    assert b'name="response_format"' in opened[0].data
    assert b'filename="audio.wav"' in opened[0].data
    assert response.payload["text"] == "hello"
    assert response.payload["language"] == "en"


def test_cancel_stops_launcher():
    launcher = FakeLauncher(_settings())
    client = SidecarSTTClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=lambda *args, **kwargs: FakeResponse(),
    )

    response = client.cancel("req-cancel")

    assert launcher.stopped == 1
    assert response.status is EnvelopeStatus.CANCELLED


def test_healthcheck_reports_launcher_status():
    launcher = FakeLauncher(_settings())
    launcher.status = RuntimeHealthStatus.STARTING
    launcher.details = "starting"
    client = SidecarSTTClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=lambda *args, **kwargs: FakeResponse(),
    )

    health = client.healthcheck()

    assert health.status is RuntimeHealthStatus.STARTING
    assert health.metadata["model_id"] == "ggml-base.en.bin"


def test_register_sidecar_stt_client_uses_explicit_sidecar_route():
    registry = RuntimeRegistry()
    client = SidecarSTTClient(
        settings=_settings(),
        launcher=FakeLauncher(_settings()),
        http_opener=lambda *args, **kwargs: FakeResponse(),
    )

    register_sidecar_stt_client(registry, client)

    assert registry.has_route(
        RuntimeRoute(
            RuntimeKind.STT,
            provider="local",
            deployment_mode="sidecar",
        )
    )