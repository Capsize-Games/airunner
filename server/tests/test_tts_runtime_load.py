"""Service-owned tests for daemon TTS runtime control."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

_SERVICES_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _SERVICES_ROOT.parent

for _path in (_PROJECT_ROOT / "services" / "src",):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)


from airunner_services.contract_enums import ModelStatus
from airunner_services.runtimes.contracts import RuntimeKind, RuntimeMode
from airunner_services.runtimes.local_fallback import LocalFallbackTTSClient
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute


class _FakeTTSWorker:
    """Minimal daemon TTS worker used by the daemon route test."""

    def __init__(self) -> None:
        self.load_calls = 0
        self.unload_calls = 0
        self._status = ModelStatus.UNLOADED

    def _load_tts(self) -> None:
        """Simulate one successful TTS load."""
        self.load_calls += 1
        self._status = ModelStatus.LOADED

    def _unload_tts(self) -> None:
        """Simulate one successful TTS unload."""
        self.unload_calls += 1
        self._status = ModelStatus.UNLOADED

    def _current_tts_status(self) -> ModelStatus:
        """Return the current fake TTS model status."""
        return self._status


class _FakeWorkerManager:
    """Expose the TTS worker through the real daemon lookup shape."""

    def __init__(self, worker: _FakeTTSWorker) -> None:
        self.tts_generator_worker = worker


class _FakeSignalSource:
    """Provide the minimal signal source surface for local fallback TTS."""

    def __init__(self, worker: _FakeTTSWorker) -> None:
        self._worker_manager = _FakeWorkerManager(worker)

    def emit_signal(self, _code, _data=None) -> None:
        """Ignore signal emissions during the daemon API test."""


def _runtime_registry(worker: _FakeTTSWorker) -> RuntimeRegistry:
    """Return one registry that exposes only the local fallback TTS route."""
    registry = RuntimeRegistry()
    client = LocalFallbackTTSClient(signal_source=_FakeSignalSource(worker))
    registry.register(
        RuntimeRoute(RuntimeKind.TTS, provider="local"),
        client,
    )
    registry.register(
        RuntimeRoute(
            RuntimeKind.TTS,
            provider="local",
            deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
        ),
        client,
    )
    return registry


def test_tts_runtime_load_uses_daemon_worker(monkeypatch) -> None:
    """The daemon TTS load route should use the daemon worker path."""
    import airunner_services.api.server as service_server
    from airunner_services.api.server import create_app

    worker = _FakeTTSWorker()
    registry = _runtime_registry(worker)
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    monkeypatch.setattr(
        service_server,
        "build_runtime_registry",
        lambda app_instance=None: registry,
    )

    app = create_app(
        allowed_origins=["http://localhost"],
        enable_cors=True,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/daemon/runtimes/tts/load",
        json={
            "provider": "local",
            "deployment_mode": "local_fallback",
            "request_id": "test-tts-load",
            "metadata": {"model_type": "OpenVoice"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "request_id": "test-tts-load",
        "status": "succeeded",
        "payload": {"model_status": "Loaded"},
        "error": None,
        "metadata": {"model_status": "Loaded"},
    }
    assert worker.load_calls == 1

    status_response = client.get(
        "/api/v1/daemon/runtimes/tts",
        params={
            "provider": "local",
            "deployment_mode": "local_fallback",
        },
    )

    assert status_response.status_code == 200
    assert status_response.json()["loaded"] is True
    assert status_response.json()["metadata"]["model_status"] == "Loaded"
