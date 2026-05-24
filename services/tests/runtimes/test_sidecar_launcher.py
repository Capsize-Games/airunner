"""Tests for the llama.cpp sidecar launcher."""

import subprocess

from airunner.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
)
from airunner.runtimes.sidecar_launcher import SidecarLauncher


class FakeResponse:
    """Minimal context-managed HTTP response."""

    def __init__(self, *, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeProcess:
    """Minimal subprocess double for launcher tests."""

    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


def _settings(model_path: str = "/tmp/model.gguf") -> LlamaCppRuntimeSettings:
    return LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=8011,
        model_path=model_path,
        model_id="qwen3-8b",
        n_ctx=4096,
        n_gpu_layers=12,
        startup_timeout_seconds=1.0,
    )


def test_command_uses_expected_llama_server_arguments(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_text("model")
    launcher = SidecarLauncher(
        _settings(str(model_path)),
        process_factory=lambda *args, **kwargs: FakeProcess(),
        health_opener=lambda *args, **kwargs: FakeResponse(),
    )

    command = launcher.command()

    assert command == [
        "llama-server",
        "--host",
        "127.0.0.1",
        "--port",
        "8011",
        "--model",
        str(model_path),
        "--ctx-size",
        "4096",
        "--n-gpu-layers",
        "12",
    ]


def test_start_spawns_and_waits_for_health(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_text("model")
    spawned = []

    def fake_process_factory(*args, **kwargs):
        spawned.append(args[0])
        return FakeProcess()

    launcher = SidecarLauncher(
        _settings(str(model_path)),
        process_factory=fake_process_factory,
        health_opener=lambda *args, **kwargs: FakeResponse(),
        sleep=lambda _seconds: None,
    )

    launcher.start()

    assert spawned[0][0] == "llama-server"
    assert launcher.is_ready() is True


def test_start_uses_runtime_layout_environment_without_file_logging(
    monkeypatch,
    tmp_path,
):
    model_path = tmp_path / "model.gguf"
    model_path.write_text("model")
    captured = {}

    def fake_process_factory(*args, **kwargs):
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path))
    launcher = SidecarLauncher(
        _settings(str(model_path)),
        process_factory=fake_process_factory,
        health_opener=lambda *args, **kwargs: FakeResponse(),
        sleep=lambda _seconds: None,
    )

    launcher.start()
    launcher.stop()

    environment = captured["kwargs"]["env"]
    assert environment["AIRUNNER_RUNTIME_ROOT"] == str(tmp_path / "runtime")
    assert environment["AIRUNNER_CACHE_DIR"] == str(tmp_path / "cache")
    assert captured["kwargs"]["stdout"] is subprocess.DEVNULL


def test_stop_terminates_running_process(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_text("model")
    process = FakeProcess()
    launcher = SidecarLauncher(
        _settings(str(model_path)),
        process_factory=lambda *args, **kwargs: process,
        health_opener=lambda *args, **kwargs: FakeResponse(),
        sleep=lambda _seconds: None,
    )

    launcher.start()
    launcher.stop()

    assert process.terminated is True


def test_start_requires_configured_model_path():
    launcher = SidecarLauncher(
        _settings(model_path=None),
        process_factory=lambda *args, **kwargs: FakeProcess(),
        health_opener=lambda *args, **kwargs: FakeResponse(),
        sleep=lambda _seconds: None,
    )

    try:
        launcher.start()
    except RuntimeError as exc:
        assert "No GGUF model is configured" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when no GGUF is configured")
