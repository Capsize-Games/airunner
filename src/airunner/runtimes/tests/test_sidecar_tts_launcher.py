"""Tests for the isolated TTS sidecar launcher."""

from pathlib import Path

import yaml

from airunner.runtimes.contracts import RuntimeHealthStatus
from airunner.runtimes.sidecar_tts_launcher import (
    SidecarTTSLauncher,
    _build_temp_daemon_config,
)
from airunner.runtimes.tts_daemon_runtime_settings import (
    TTSDaemonRuntimeSettings,
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


def test_start_spawns_daemon_with_tts_only_environment(tmp_path):
    process = FakeProcess()
    captured = {}
    config_path = tmp_path / "tts-runtime.yaml"
    config_path.write_text("server: {}\n", encoding="utf-8")

    def process_factory(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return process

    launcher = SidecarTTSLauncher(
        _settings(),
        process_factory=process_factory,
        health_opener=lambda *args, **kwargs: FakeResponse(),
        config_path_builder=lambda _settings: config_path,
        launch_preparer=lambda: None,
    )

    launcher.start()

    assert captured["command"][:3] == [
        launcher.command()[0],
        "-m",
        "airunner.services.daemon",
    ]
    environment = captured["kwargs"]["env"]
    assert environment["AIRUNNER_TTS_ON"] == "1"
    assert environment["AIRUNNER_SD_ON"] == "0"
    assert environment["AIRUNNER_TTS_SIDECAR_PROCESS"] == "1"


def test_stop_terminates_process_and_cleans_temp_config(tmp_path):
    process = FakeProcess()
    config_path = tmp_path / "tts-runtime.yaml"
    config_path.write_text("server: {}\n", encoding="utf-8")
    launcher = SidecarTTSLauncher(
        _settings(),
        process_factory=lambda *args, **kwargs: process,
        health_opener=lambda *args, **kwargs: FakeResponse(),
        config_path_builder=lambda _settings: config_path,
        launch_preparer=lambda: None,
    )
    launcher.start()

    launcher.stop()

    assert process.terminated == 1
    assert config_path.exists() is False


def test_health_status_reports_ready(tmp_path):
    process = FakeProcess()
    config_path = tmp_path / "tts-runtime.yaml"
    config_path.write_text("server: {}\n", encoding="utf-8")
    launcher = SidecarTTSLauncher(
        _settings(),
        process_factory=lambda *args, **kwargs: process,
        health_opener=lambda *args, **kwargs: FakeResponse(),
        config_path_builder=lambda _settings: Path(config_path),
        launch_preparer=lambda: None,
    )

    launcher.start()
    status, details = launcher.health_status()

    assert status is RuntimeHealthStatus.READY
    assert details == "ready"


def test_temp_daemon_config_uses_standard_runtime_directories(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path))

    config_path = _build_temp_daemon_config(_settings())
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    finally:
        config_path.unlink(missing_ok=True)

    assert config_path.parent == tmp_path / "runtime" / "configs"
    assert config["logging"]["file"] == str(
        tmp_path / "runtime" / "logs" / "tts-runtime.log"
    )
    assert config["health"]["heartbeat_file"] == str(
        tmp_path / "runtime" / "tts-runtime.heartbeat"
    )