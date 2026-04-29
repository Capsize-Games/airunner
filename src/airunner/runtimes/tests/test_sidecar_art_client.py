"""Tests for the isolated art sidecar runtime client."""

import base64

from airunner.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner.runtimes.art_daemon_runtime_settings import (
    ArtDaemonRuntimeSettings,
)
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeHealthStatus,
    RuntimeKind,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner.runtimes.sidecar_art_client import (
    SidecarArtClient,
    register_sidecar_art_client,
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
    """Minimal requests session double for art client tests."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)

    def close(self):
        return None


class FakeLauncher:
    """Minimal launcher double for art client tests."""

    def __init__(self, settings):
        self.settings = settings
        self.endpoint = settings.endpoint
        self.api_base_url = f"{settings.endpoint}/api/v1/art"
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def health_status(self):
        return RuntimeHealthStatus.READY, "ready"


def _settings() -> ArtDaemonRuntimeSettings:
    return ArtDaemonRuntimeSettings(
        host="127.0.0.1",
        port=8190,
        base_daemon_config_path=None,
        art_model_path="/tmp/art-model",
        art_model_version="SDXL 1.0",
        art_scheduler="DDIM",
        startup_timeout_seconds=1.0,
        request_timeout_seconds=1.0,
        invocation_timeout_seconds=10.0,
        status_poll_interval_seconds=0.01,
    )


def _request(action: RuntimeAction = RuntimeAction.INVOKE) -> RequestEnvelope:
    return RequestEnvelope(
        request_id="art-req-1",
        runtime=RuntimeKind.ART,
        action=action,
        payload={
            "prompt": "Draw a lighthouse",
            "negative_prompt": "",
            "model": "/tmp/request-model",
            "width": 512,
            "height": 512,
            "steps": 20,
            "cfg_scale": 7.5,
            "seed": 123,
            "num_images": 1,
            "metadata": {
                "version": "Z-Image Turbo",
                "scheduler": "Flow Match Euler",
            },
        },
    )


def test_load_model_starts_launcher():
    launcher = FakeLauncher(_settings())
    client = SidecarArtClient(
        settings=_settings(),
        launcher=launcher,
        session=FakeSession([]),
    )

    response = client.invoke(_request(RuntimeAction.LOAD_MODEL))

    assert launcher.started == 1
    assert response.status is EnvelopeStatus.SUCCEEDED


def test_invoke_round_trips_art_job_api(monkeypatch):
    monkeypatch.setattr(
        "airunner.runtimes.sidecar_art_client.time.sleep",
        lambda _seconds: None,
    )
    launcher = FakeLauncher(_settings())
    session = FakeSession(
        [
            FakeResponse(payload={"job_id": "job-1", "status": "running"}),
            FakeResponse(payload={"job_id": "job-1", "status": "running"}),
            FakeResponse(
                payload={"job_id": "job-1", "status": "completed"}
            ),
            FakeResponse(content=b"png-bytes"),
        ]
    )
    client = SidecarArtClient(
        settings=_settings(),
        launcher=launcher,
        session=session,
    )

    response = client.invoke(_request())

    assert launcher.started == 1
    assert response.status is EnvelopeStatus.SUCCEEDED
    assert response.payload["image_count"] == 1
    assert response.payload["images"] == [
        base64.b64encode(b"png-bytes").decode("ascii")
    ]
    assert session.calls[0][0] == "POST"
    assert session.calls[0][1].endswith("/api/v1/art/generate")
    assert session.calls[0][2]["json"] == {
        "prompt": "Draw a lighthouse",
        "negative_prompt": "",
        "model": "/tmp/request-model",
        "width": 512,
        "height": 512,
        "steps": 20,
        "cfg_scale": 7.5,
        "seed": 123,
        "num_images": 1,
        "version": "Z-Image Turbo",
        "scheduler": "Flow Match Euler",
    }


def test_invoke_with_progress_reports_polled_job_updates(monkeypatch):
    monkeypatch.setattr(
        "airunner.runtimes.sidecar_art_client.time.sleep",
        lambda _seconds: None,
    )
    progress_updates = []
    launcher = FakeLauncher(_settings())
    session = FakeSession(
        [
            FakeResponse(payload={"job_id": "job-1", "status": "running"}),
            FakeResponse(payload={"job_id": "job-1", "status": "running", "progress": 12.5}),
            FakeResponse(payload={"job_id": "job-1", "status": "running", "progress": 75.0}),
            FakeResponse(payload={"job_id": "job-1", "status": "completed", "progress": 100.0}),
            FakeResponse(content=b"png-bytes"),
        ]
    )
    client = SidecarArtClient(
        settings=_settings(),
        launcher=launcher,
        session=session,
    )

    response = client.invoke_with_progress(_request(), progress_updates.append)

    assert response.status is EnvelopeStatus.SUCCEEDED
    assert progress_updates == [
        {
            "job_id": "job-1",
            "status": "running",
            "progress": 2.0,
            "phase": "submitted",
        },
        {"job_id": "job-1", "status": "running", "progress": 12.5},
        {"job_id": "job-1", "status": "running", "progress": 75.0},
        {"job_id": "job-1", "status": "completed", "progress": 100.0},
    ]


def test_cancel_sends_remote_job_cancel():
    launcher = FakeLauncher(_settings())
    session = FakeSession([FakeResponse(payload={"status": "cancelled"})])
    client = SidecarArtClient(
        settings=_settings(),
        launcher=launcher,
        session=session,
    )
    client._active_jobs["art-cancel-1"] = "job-9"

    response = client.cancel("art-cancel-1")

    assert response.status is EnvelopeStatus.CANCELLED
    assert session.calls[0][0] == "DELETE"
    assert session.calls[0][1].endswith("/api/v1/art/cancel/job-9")


def test_healthcheck_reports_launcher_status():
    launcher = FakeLauncher(_settings())
    client = SidecarArtClient(
        settings=_settings(),
        launcher=launcher,
        session=FakeSession([]),
    )

    health = client.healthcheck()

    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata["model_version"] == "SDXL 1.0"


def test_register_sidecar_art_client_uses_explicit_sidecar_route():
    registry = RuntimeRegistry()
    client = SidecarArtClient(
        settings=_settings(),
        launcher=FakeLauncher(_settings()),
        session=FakeSession([]),
    )

    register_sidecar_art_client(registry, client)

    assert registry.has_route(
        RuntimeRoute(
            RuntimeKind.ART,
            provider="local",
            deployment_mode="sidecar",
        )
    )