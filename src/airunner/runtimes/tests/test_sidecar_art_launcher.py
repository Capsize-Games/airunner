"""Tests for the isolated art sidecar launcher."""

from pathlib import Path

from airunner.runtimes.art_daemon_runtime_settings import (
    ArtDaemonRuntimeSettings,
)
from airunner.runtimes.contracts import RuntimeHealthStatus
from airunner.runtimes.sidecar_art_launcher import SidecarArtLauncher


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


def test_start_spawns_daemon_with_art_only_environment(tmp_path):
    process = FakeProcess()
    captured = {}
    config_path = tmp_path / "art-runtime.yaml"
    config_path.write_text("server: {}\n", encoding="utf-8")

    def process_factory(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return process

    launcher = SidecarArtLauncher(
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
    assert environment["AIRUNNER_SD_ON"] == "1"
    assert environment["AIRUNNER_LLM_ON"] == "0"
    assert environment["AIRUNNER_ART_SIDECAR_PROCESS"] == "1"


def test_stop_terminates_process_and_cleans_temp_config(tmp_path):
    process = FakeProcess()
    config_path = tmp_path / "art-runtime.yaml"
    config_path.write_text("server: {}\n", encoding="utf-8")
    launcher = SidecarArtLauncher(
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
    config_path = tmp_path / "art-runtime.yaml"
    config_path.write_text("server: {}\n", encoding="utf-8")
    launcher = SidecarArtLauncher(
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