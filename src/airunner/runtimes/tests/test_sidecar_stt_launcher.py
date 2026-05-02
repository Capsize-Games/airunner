"""Tests for the whisper.cpp sidecar launcher."""

import subprocess

from airunner.runtimes.contracts import RuntimeHealthStatus
from airunner.runtimes.sidecar_stt_launcher import SidecarSTTLauncher
from airunner.runtimes.whisper_cpp_runtime_settings import (
    WhisperCppRuntimeSettings,
)


class FakeResponse:
    """Minimal context-managed health response."""

    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeProcess:
    """Minimal subprocess double for launcher tests."""

    def __init__(self):
        self.returncode = None
        self.terminated = 0
        self.killed = 0

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated += 1
        self.returncode = 0

    def wait(self, timeout):
        return self.returncode

    def kill(self):
        self.killed += 1
        self.returncode = -9


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


def test_command_includes_whisper_server_flags(monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda _path: True)
    launcher = SidecarSTTLauncher(_settings())

    command = launcher.command()

    assert command[:2] == ["whisper-server", "--host"]
    assert "--inference-path" in command
    assert "/inference" in command


def test_start_spawns_process_and_waits_for_health(monkeypatch):
    process = FakeProcess()
    monkeypatch.setattr("os.path.exists", lambda _path: True)
    launcher = SidecarSTTLauncher(
        _settings(),
        process_factory=lambda *args, **kwargs: process,
        health_opener=lambda *args, **kwargs: FakeResponse(),
    )

    launcher.start()

    assert launcher.is_running() is True
    assert launcher.health_status()[0] is RuntimeHealthStatus.READY


def test_start_uses_runtime_layout_environment_without_file_logging(
    monkeypatch,
    tmp_path,
):
    process = FakeProcess()
    captured = {}

    def process_factory(*args, **kwargs):
        captured["kwargs"] = kwargs
        return process

    monkeypatch.setattr("os.path.exists", lambda _path: True)
    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path))
    launcher = SidecarSTTLauncher(
        _settings(),
        process_factory=process_factory,
        health_opener=lambda *args, **kwargs: FakeResponse(),
    )

    launcher.start()
    launcher.stop()

    environment = captured["kwargs"]["env"]
    assert environment["AIRUNNER_RUNTIME_ROOT"] == str(tmp_path / "runtime")
    assert environment["AIRUNNER_CACHE_DIR"] == str(tmp_path / "cache")
    assert captured["kwargs"]["stdout"] is subprocess.DEVNULL


def test_stop_terminates_running_process(monkeypatch):
    process = FakeProcess()
    monkeypatch.setattr("os.path.exists", lambda _path: True)
    launcher = SidecarSTTLauncher(
        _settings(),
        process_factory=lambda *args, **kwargs: process,
        health_opener=lambda *args, **kwargs: FakeResponse(),
    )
    launcher.start()

    launcher.stop()

    assert process.terminated == 1


def test_health_status_reports_failed_exit(monkeypatch):
    process = FakeProcess()
    process.returncode = 9
    monkeypatch.setattr("os.path.exists", lambda _path: True)
    launcher = SidecarSTTLauncher(
        _settings(),
        process_factory=lambda *args, **kwargs: process,
        health_opener=lambda *args, **kwargs: FakeResponse(),
    )
    launcher._process = process

    status, details = launcher.health_status()

    assert status is RuntimeHealthStatus.FAILED
    assert "code 9" in details