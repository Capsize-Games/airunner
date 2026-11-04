"""Private credentials for the supervised whisper.cpp child."""

from __future__ import annotations

import base64
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from airunner_services.api import loopback_token
from airunner_services.runtimes import sidecar_stt_launcher
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.runtimes.sidecar_stt_launcher import SidecarSTTLauncher
from airunner_services.runtimes.whisper_cpp_runtime_settings import (
    WhisperCppRuntimeSettings,
)


class _Process:
    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return None

    def kill(self):
        pass


class _HealthResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _settings(model_path: Path, **overrides) -> WhisperCppRuntimeSettings:
    values = {
        "executable": "whisper-server",
        "host": "127.0.0.1",
        "port": 18012,
        "model_path": str(model_path),
        "model_id": "private-test-model",
        "n_threads": 2,
        "n_processors": 1,
        "language": "auto",
        "request_path": "/private",
        "inference_path": "/inference",
        "convert_audio": False,
        "use_gpu": False,
        "startup_timeout_seconds": 1.0,
    }
    values.update(overrides)
    return WhisperCppRuntimeSettings(**values)


def test_launcher_persists_private_key_file_without_putting_secret_in_argv(
    tmp_path: Path, monkeypatch
) -> None:
    token_file = tmp_path / "config" / "loopback_token"
    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path / "airunner"))
    monkeypatch.setattr(loopback_token, "loopback_token_path", lambda: token_file)
    monkeypatch.setattr(sidecar_stt_launcher, "loopback_token_path", lambda: token_file)
    monkeypatch.setattr(loopback_token, "_cached_token", None)
    monkeypatch.setattr(loopback_token, "_cache_loaded", False)
    model_path = tmp_path / "ggml-fixture.bin"
    model_path.write_bytes(b"synthetic model path fixture")
    argv: list[str] = []

    launcher = SidecarSTTLauncher(
        _settings(model_path),
        process_factory=lambda command, **_kwargs: (
            argv.extend(command),
            _Process(),
        )[1],
        health_opener=lambda *_args, **_kwargs: _HealthResponse(),
        sleep=lambda _seconds: None,
        time_fn=lambda: 0.0,
    )
    assert launcher.command()[launcher.command().index("--api-key-file") + 1] == str(
        token_file
    )

    launcher.start()

    token = token_file.read_text(encoding="utf-8").strip()
    assert stat.S_IMODE(token_file.stat().st_mode) == 0o600
    assert token
    assert token not in argv
    assert launcher.internal_auth_headers() == {
        "Authorization": f"Bearer {token}"
    }
    assert argv[argv.index("--api-key-file") + 1] == str(token_file)
    assert argv[argv.index("--host") + 1] == "127.0.0.1"
    launcher.stop()
    loopback_token._cached_token = None
    loopback_token._cache_loaded = False


def test_stt_inference_sends_bearer_to_prefixed_child_route() -> None:
    from airunner_services.runtimes.sidecar_stt_client import SidecarSTTClient

    settings = _settings(Path("/not-loaded/ggml.bin"))
    observed = {}

    class Launcher:
        endpoint = settings.endpoint
        inference_url = f"{settings.endpoint}/private/inference"

        def start(self):
            pass

        def stop(self):
            pass

        def health_status(self):
            return None, "ready"

        def internal_auth_headers(self):
            return {"Authorization": "Bearer fixture-private-token"}

    class Response:
        def read(self, _limit=None):
            return b'{"text":"fixture result"}'

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def opener(request, timeout=None):
        observed["url"] = request.full_url
        observed["authorization"] = request.get_header("Authorization")
        observed["timeout"] = timeout
        return Response()

    client = SidecarSTTClient(
        settings=settings,
        launcher=Launcher(),
        http_opener=opener,
    )
    request = SimpleNamespace(
        runtime=RuntimeKind.STT,
        action=RuntimeAction.INVOKE,
        request_id="authenticated-stt",
        payload={
            "audio_b64": base64.b64encode(b"RIFF synthetic audio").decode(),
            "mime_type": "audio/wav",
        },
    )

    response = client.invoke(request)

    assert observed["url"] == f"{settings.endpoint}/private/inference"
    assert observed["authorization"] == "Bearer fixture-private-token"
    assert "fixture-private-token" not in observed["url"]
    assert response.payload["text"] == "fixture result"


@pytest.mark.parametrize("defect", ["symlink", "public-mode", "missing", "mismatch"])
def test_invalid_credential_file_prevents_child_start(tmp_path, monkeypatch, defect):
    token_path = tmp_path / "child-token"
    token_path.write_text("fixture-token")
    token_path.chmod(0o600)
    if defect == "symlink":
        token_path.rename(tmp_path / "target")
        token_path.symlink_to(tmp_path / "target")
    elif defect == "public-mode":
        token_path.chmod(0o644)
    elif defect == "missing":
        token_path.unlink()
    monkeypatch.setattr(sidecar_stt_launcher, "loopback_token_path", lambda: token_path)
    monkeypatch.setattr(sidecar_stt_launcher, "get_or_create_loopback_token", lambda: "fixture-token")
    monkeypatch.setattr(sidecar_stt_launcher, "load_loopback_token", lambda: "different" if defect == "mismatch" else "fixture-token")
    launcher = SidecarSTTLauncher(
        _settings(tmp_path / "not-loaded.bin"),
        process_factory=lambda *_args, **_kwargs: pytest.fail("child spawned with unsafe credential"),
    )
    with pytest.raises(RuntimeError, match="private local runtime credential"):
        launcher.start()
    assert launcher.internal_auth_headers() == {}
