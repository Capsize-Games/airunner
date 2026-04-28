"""Tests for the isolated TTS sidecar runtime client."""

import base64

from airunner.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeHealthStatus,
    RuntimeKind,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner.runtimes.sidecar_tts_client import (
    SidecarTTSClient,
    register_sidecar_tts_client,
)
from airunner.runtimes.tts_daemon_runtime_settings import (
    TTSDaemonRuntimeSettings,
)


class FakeResponse:
    """Minimal requests.Response-style double."""

    def __init__(self, *, payload=None, content: bytes = b"", text: str = ""):
        self._payload = payload or {}
        self.content = content
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeSession:
    """Minimal requests session double for TTS client tests."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)

    def close(self):
        return None


class FakeLauncher:
    """Minimal launcher double for TTS client tests."""

    def __init__(self, settings):
        self.settings = settings
        self.endpoint = settings.endpoint
        self.api_base_url = f"{settings.endpoint}/api/v1/tts"
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def is_running(self):
        return True

    def health_status(self):
        return RuntimeHealthStatus.READY, "ready"


def _settings() -> TTSDaemonRuntimeSettings:
    return TTSDaemonRuntimeSettings(
        host="127.0.0.1",
        port=8191,
        base_daemon_config_path=None,
        tts_model_path="/tmp/tts-model",
        tts_model_type="openvoice",
        startup_timeout_seconds=1.0,
        request_timeout_seconds=2.0,
    )


def _request(action: RuntimeAction = RuntimeAction.INVOKE) -> RequestEnvelope:
    return RequestEnvelope(
        request_id="tts-req-1",
        runtime=RuntimeKind.TTS,
        action=action,
        payload={
            "text": "Read this sentence aloud.",
            "voice": "alloy",
            "speed": 1.0,
        },
    )


def test_load_model_starts_launcher():
    launcher = FakeLauncher(_settings())
    client = SidecarTTSClient(
        settings=_settings(),
        launcher=launcher,
        session=FakeSession([]),
    )

    response = client.invoke(_request(RuntimeAction.LOAD_MODEL))

    assert launcher.started == 1
    assert response.status is EnvelopeStatus.SUCCEEDED


def test_invoke_returns_base64_audio_payload():
    launcher = FakeLauncher(_settings())
    session = FakeSession([FakeResponse(content=b"wav-bytes")])
    client = SidecarTTSClient(
        settings=_settings(),
        launcher=launcher,
        session=session,
    )

    response = client.invoke(_request())

    assert launcher.started == 1
    assert response.status is EnvelopeStatus.SUCCEEDED
    assert response.payload["accepted"] is True
    assert response.payload["audio_b64"] == base64.b64encode(
        b"wav-bytes"
    ).decode("ascii")
    assert session.calls[0][0] == "POST"
    assert session.calls[0][1].endswith("/api/v1/tts/synthesize")


def test_cancel_calls_remote_tts_runtime_cancel():
    launcher = FakeLauncher(_settings())
    session = FakeSession([FakeResponse(payload={"status": "cancelled"})])
    client = SidecarTTSClient(
        settings=_settings(),
        launcher=launcher,
        session=session,
    )
    client._active_requests.add("tts-cancel-1")

    response = client.cancel("tts-cancel-1")

    assert response.status is EnvelopeStatus.CANCELLED
    assert session.calls[0][0] == "POST"
    assert session.calls[0][1].endswith("/api/v1/daemon/runtimes/tts/cancel")


def test_healthcheck_reports_launcher_status():
    launcher = FakeLauncher(_settings())
    client = SidecarTTSClient(
        settings=_settings(),
        launcher=launcher,
        session=FakeSession([]),
    )

    health = client.healthcheck()

    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_type"] == "openvoice"


def test_register_sidecar_tts_client_uses_explicit_sidecar_route():
    registry = RuntimeRegistry()
    client = SidecarTTSClient(
        settings=_settings(),
        launcher=FakeLauncher(_settings()),
        session=FakeSession([]),
    )

    register_sidecar_tts_client(registry, client)

    assert registry.has_route(
        RuntimeRoute(
            RuntimeKind.TTS,
            provider="local",
            deployment_mode="sidecar",
        )
    )