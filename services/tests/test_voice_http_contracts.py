"""Authenticated STT and TTS HTTP contracts with fake runtime boundaries."""

from __future__ import annotations

import base64
import io
import struct
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.server import create_app
from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner_services.runtimes.contracts import RuntimeHealthStatus


class _FakeTTSClient:
    def __init__(self, health=None) -> None:
        self.envelopes = []
        self.health = health

    def healthcheck(self):
        if self.health is None:
            raise RuntimeError("health unavailable")
        return self.health

    def invoke(self, envelope):
        self.envelopes.append(envelope)
        return ResponseEnvelope(
            request_id=envelope.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"audio_b64": base64.b64encode(b"wav").decode("ascii")},
        )


class _FakeSTTClient:
    def __init__(self, status: str, metadata: dict | None) -> None:
        self.health = SimpleNamespace(
            status=status,
            metadata=metadata or {},
        )

    def healthcheck(self):
        return self.health


class _FakeRegistry:
    def __init__(self, client=None) -> None:
        self.client = client

    def resolve(self, *_args, **_kwargs):
        if self.client is None:
            raise KeyError("runtime unavailable")
        return self.client


@pytest.fixture()
def authenticated_client(tmp_path, monkeypatch):
    """Build an app with an isolated loopback token and base directory."""
    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda _c: True)
    monkeypatch.setattr(
        loopback_token,
        "loopback_token_path",
        lambda: Path(tmp_path) / "config" / "loopback_token",
    )
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None
    app = create_app()
    token = loopback_token.get_or_create_loopback_token()
    yield TestClient(app), {"X-Airunner-Token": token}, app
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None


def test_tts_http_accepts_bounded_request_and_returns_wav(
    authenticated_client,
) -> None:
    client, headers, app = authenticated_client
    runtime = _FakeTTSClient()
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.post(
        "/api/v1/tts/synthesize",
        headers=headers,
        json={"text": "hello", "voice": "voice-id", "speed": 0.25},
    )

    assert response.status_code == 200
    assert response.content == b"wav"
    invocation = runtime.envelopes[0].payload
    assert invocation["text"] == "hello"
    assert invocation["voice"] == "voice-id"
    assert invocation["speed"] == 0.25


def test_espeak_model_type_uses_headless_cli_through_authenticated_route(
    authenticated_client, monkeypatch
) -> None:
    from airunner_services.runtimes.espeak_cli_renderer import EspeakCliRenderer
    from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient

    client, headers, app = authenticated_client
    voice_table = b"""Pty Language Age/Gender VoiceName File Other Languages
 5 en-us --/M English_(America) gmw/en-US
"""
    frames = b"\x00\x00" * 20
    streaming_wav = (
        b"RIFF"
        + struct.pack("<I", 0xFFFFFFFF)
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, 22050, 44100, 2, 16)
        + b"data"
        + struct.pack("<I", 0xFFFFFFFF)
        + frames
    )

    class FakeProcess:
        def __init__(self, output: bytes) -> None:
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(output)
            self.returncode = 0
            self.waited = False

        def wait(self, timeout=None):
            self.waited = True
            return self.returncode

        def poll(self):
            return self.returncode if self.waited else None

        def kill(self):
            self.returncode = -9

    calls = []

    def fake_popen(argv, **kwargs):
        calls.append(argv)
        output = voice_table if argv[-1] == "--voices" else streaming_wav
        return FakeProcess(output)

    class LazyWorkerManager:
        @property
        def tts_generator_worker(self):
            raise AssertionError("eSpeak CLI route created playback worker")

    runtime = LocalFallbackTTSClient(
        signal_source=SimpleNamespace(_worker_manager=LazyWorkerManager()),
        mediator=SimpleNamespace(),
    )
    runtime._espeak_cli_renderer = EspeakCliRenderer(popen=fake_popen)
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.post(
        "/api/v1/tts/synthesize",
        headers=headers,
        json={
            "text": "route check",
            "voice": "en-us",
            "speed": 1.0,
            "model_type": "Espeak",
        },
    )

    assert response.status_code == 200
    assert response.content[:4] == b"RIFF"
    assert response.content[8:12] == b"WAVE"
    assert struct.unpack_from("<I", response.content, 4)[0] == len(response.content) - 8
    assert calls[1][1] == "--stdout"
    assert "-m" not in calls[1]


@pytest.mark.parametrize(
    "failure,voice,speed,expected_status,expected_code,retryable",
    [
        (
            "unknown_voice",
            "not-listed",
            1.0,
            422,
            "tts_unsupported_parameter",
            False,
        ),
        (
            "unsupported_speed",
            "en-us",
            0.25,
            422,
            "tts_unsupported_parameter",
            False,
        ),
        (
            "missing_binary",
            "en-us",
            1.0,
            503,
            "tts_backend_unavailable",
            True,
        ),
        ("timeout", "en-us", 1.0, 504, "tts_timeout", True),
    ],
)
def test_espeak_route_preserves_runtime_error_categories(
    authenticated_client,
    failure,
    voice,
    speed,
    expected_status,
    expected_code,
    retryable,
) -> None:
    from airunner_services.runtimes.espeak_cli_renderer import EspeakCliRenderer
    from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient

    client, headers, app = authenticated_client
    voice_table = b"""Pty Language Age/Gender VoiceName File Other Languages
 5 en-us --/M English_(America) gmw/en-US
"""

    class FakeProcess:
        def __init__(self, output: bytes = b"") -> None:
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(output)
            self.returncode = 0
            self.waited = False

        def wait(self, timeout=None):
            self.waited = True
            return self.returncode

        def poll(self):
            return self.returncode if self.waited or self.returncode else None

        def kill(self):
            self.returncode = -9

    class TimeoutProcess(FakeProcess):
        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("espeak-ng", timeout)
            self.waited = True
            return self.returncode

    calls = []

    def fake_popen(argv, **kwargs):
        calls.append(argv)
        if failure == "missing_binary":
            raise FileNotFoundError("binary unavailable")
        if failure == "timeout" and argv[-1] != "--voices":
            return TimeoutProcess()
        return FakeProcess(voice_table)

    class LazyWorkerManager:
        @property
        def tts_generator_worker(self):
            raise AssertionError("eSpeak CLI route created playback worker")

    class RecordingRuntime(LocalFallbackTTSClient):
        last_response = None

        def invoke(self, envelope):
            self.last_response = super().invoke(envelope)
            return self.last_response

    runtime = RecordingRuntime(
        signal_source=SimpleNamespace(_worker_manager=LazyWorkerManager()),
        mediator=SimpleNamespace(),
    )
    runtime._espeak_cli_renderer = EspeakCliRenderer(popen=fake_popen)
    app.state.runtime_registry = _FakeRegistry(runtime)
    response = client.post(
        "/api/v1/tts/synthesize",
        headers=headers,
        json={
            "text": "route error check",
            "voice": voice,
            "speed": speed,
            "model_type": "Espeak",
        },
    )

    assert response.status_code == expected_status
    assert runtime.last_response.error.code == expected_code
    assert runtime.last_response.error.retryable is retryable
    if failure == "unsupported_speed":
        assert calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "   "},
        {"text": "x" * 5001},
        {"text": "hello", "speed": 0.249},
        {"text": "hello", "speed": 4.001},
        {"text": "hello", "speed": "NaN"},
        {"text": "hello", "speed": "Infinity"},
        {"text": "hello", "speed": "1.0"},
        {"text": "hello", "voice": 12},
        {"text": "hello", "voice": "bad\r\nname"},
        {"text": "hello", "model": " "},
    ],
)
def test_tts_http_rejects_invalid_payload_before_runtime(
    authenticated_client, payload: dict
) -> None:
    client, headers, app = authenticated_client
    runtime = _FakeTTSClient()
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.post(
        "/api/v1/tts/synthesize", headers=headers, json=payload
    )

    assert response.status_code == 422
    assert runtime.envelopes == []


def test_tts_voice_catalog_uses_ready_runtime_health_metadata(
    authenticated_client,
) -> None:
    client, headers, app = authenticated_client
    runtime = _FakeTTSClient(
        SimpleNamespace(
            status=RuntimeHealthStatus.READY,
            metadata={"voice_ids": ["default"]},
        )
    )
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.get("/api/v1/tts/voices", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"voices": ["default"]}


def test_tts_voice_catalog_reports_unavailable_when_not_provided(
    authenticated_client,
) -> None:
    client, headers, app = authenticated_client
    runtime = _FakeTTSClient(
        SimpleNamespace(
            status=RuntimeHealthStatus.STOPPED,
            metadata={"voice_ids": ["default"]},
        )
    )
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.get("/api/v1/tts/voices", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "tts_voice_catalog_unavailable"


def test_tts_voice_catalog_hides_deferred_openvoice_even_if_ready(
    authenticated_client,
) -> None:
    client, headers, app = authenticated_client
    runtime = _FakeTTSClient(
        SimpleNamespace(
            status=RuntimeHealthStatus.READY,
            metadata={
                "model_type": "OpenVoice",
                "voice_ids": ["default"],
            },
        )
    )
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.get("/api/v1/tts/voices", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "tts_voice_catalog_unavailable"


def test_tts_http_rejects_explicit_deferred_backend_before_runtime(
    authenticated_client,
) -> None:
    client, headers, app = authenticated_client
    runtime = _FakeTTSClient()
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.post(
        "/api/v1/tts/synthesize",
        headers=headers,
        json={"text": "hello", "model_type": "OpenVoice"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "tts_backend_unavailable"
    assert runtime.envelopes == []


@pytest.mark.parametrize(
    ("status", "metadata", "expected_loaded"),
    [
        (RuntimeHealthStatus.READY, {"model_id": "ggml-large-v3.bin"}, True),
        (RuntimeHealthStatus.STOPPED, {"model_id": "ggml-large-v3.bin"}, False),
        (RuntimeHealthStatus.READY, {"model_id": "other-model.bin"}, False),
        (RuntimeHealthStatus.READY, {}, False),
    ],
)
def test_stt_catalog_loaded_requires_ready_matching_identity(
    authenticated_client, status, metadata, expected_loaded: bool
) -> None:
    client, headers, app = authenticated_client
    app.state.runtime_registry = _FakeRegistry(
        _FakeSTTClient(status, metadata)
    )

    response = client.get("/api/v1/stt/models", headers=headers)

    assert response.status_code == 200
    models = response.json()
    assert len(models) == 1
    assert models[0]["id"] == "openai/whisper-large-v3"
    assert models[0]["loaded"] is expected_loaded


def test_stt_catalog_marks_models_unloaded_when_runtime_is_unavailable(
    authenticated_client,
) -> None:
    client, headers, app = authenticated_client
    app.state.runtime_registry = None

    response = client.get("/api/v1/stt/models", headers=headers)

    assert response.status_code == 200
    assert all(model["loaded"] is False for model in response.json())


class _LoadedOpenVoiceWorker:
    def __init__(self, status) -> None:
        self.status = status

    def _current_tts_status(self):
        return self.status

    @staticmethod
    def _active_tts_model():
        return "OpenVoice"


class _LazyWorkerManager:
    def __init__(self, worker=None) -> None:
        self._tts_generator_worker = worker
        self.access_count = 0

    @property
    def tts_generator_worker(self):
        self.access_count += 1
        raise AssertionError("health must not resolve the lazy worker property")


def test_production_fallback_does_not_report_deferred_openvoice_as_ready(
    authenticated_client,
) -> None:
    from airunner_common.contract_enums import ModelStatus
    from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient

    client, headers, app = authenticated_client
    worker_manager = _LazyWorkerManager(
        _LoadedOpenVoiceWorker(ModelStatus.LOADED)
    )
    runtime = LocalFallbackTTSClient(
        signal_source=SimpleNamespace(_worker_manager=worker_manager),
        mediator=SimpleNamespace(),
    )
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.get("/api/v1/tts/voices", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "tts_voice_catalog_unavailable"
    assert worker_manager.access_count == 0


def test_unloaded_fallback_voice_lookup_does_not_create_worker(
    authenticated_client,
) -> None:
    from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient

    client, headers, app = authenticated_client
    worker_manager = _LazyWorkerManager()
    runtime = LocalFallbackTTSClient(
        signal_source=SimpleNamespace(_worker_manager=worker_manager),
        mediator=SimpleNamespace(),
    )
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.get("/api/v1/tts/voices", headers=headers)

    assert response.status_code == 503
    assert worker_manager.access_count == 0


def test_sidecar_openvoice_health_is_deferred_without_child_check(
    authenticated_client, monkeypatch
) -> None:
    from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient
    from airunner_services.runtimes.tts_daemon_runtime_settings import (
        TTSDaemonRuntimeSettings,
    )

    class _ReadyLauncher:
        endpoint = "http://127.0.0.1:8191"
        api_base_url = endpoint + "/api/v1/tts"

        health_checks = 0

        def health_status(self):
            self.health_checks += 1
            return RuntimeHealthStatus.READY, "ready"

    settings = TTSDaemonRuntimeSettings(
        host="127.0.0.1",
        port=8191,
        base_daemon_config_path=None,
        tts_model_path=None,
        tts_model_type="OpenVoice",
        startup_timeout_seconds=1.0,
        request_timeout_seconds=1.0,
    )
    runtime = SidecarTTSClient(
        settings=settings,
        launcher=_ReadyLauncher(),
    )
    inner_summary = []
    monkeypatch.setattr(
        runtime,
        "_inner_runtime_summary",
        lambda: inner_summary.append(True) or {
            "status": "ready",
            "metadata": {"voice_ids": ["default"]},
        },
    )
    client, headers, app = authenticated_client
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.get("/api/v1/tts/voices", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "tts_voice_catalog_unavailable"
    assert runtime.healthcheck().metadata["capability_status"] == "deferred"
    assert inner_summary == []


@pytest.mark.parametrize(
    ("status", "metadata", "expected_models"),
    [
        (
            RuntimeHealthStatus.READY,
            {"model_id": "local-tts-1", "model_name": "Local TTS"},
            [{"id": "local-tts-1", "name": "Local TTS", "loaded": True}],
        ),
        (
            RuntimeHealthStatus.STOPPED,
            {"model_id": "local-tts-1", "model_name": "Local TTS"},
            [],
        ),
        (
            RuntimeHealthStatus.READY,
            {"model_id": "openvoice-v2", "model_type": "OpenVoice"},
            [],
        ),
        (
            RuntimeHealthStatus.READY,
            {"model_type": "Espeak"},
            [],
        ),
    ],
)
def test_tts_catalog_loaded_requires_ready_matching_identity(
    authenticated_client, status, metadata, expected_models: list[dict]
) -> None:
    client, headers, app = authenticated_client
    runtime = _FakeTTSClient(
        SimpleNamespace(status=status, metadata=metadata)
    )
    app.state.runtime_registry = _FakeRegistry(runtime)

    response = client.get("/api/v1/tts/models", headers=headers)

    assert response.status_code == 200
    assert response.json() == expected_models


def test_tts_and_stt_routes_reject_missing_authentication(
    authenticated_client,
) -> None:
    client, _headers, app = authenticated_client
    app.state.runtime_registry = _FakeRegistry(_FakeTTSClient())

    for response in (
        client.get("/api/v1/tts/voices"),
        client.get("/api/v1/stt/models"),
        client.post("/api/v1/tts/synthesize", json={"text": "hello"}),
    ):
        assert response.status_code in {401, 403}
