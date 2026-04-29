"""Tests for the isolated art sidecar launcher."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import airunner.runtimes.sidecar_art_launcher as sidecar_art_launcher_module
from airunner.runtimes.art_daemon_runtime_settings import (
    ArtDaemonRuntimeSettings,
)
from airunner.runtimes.contracts import RuntimeHealthStatus
from airunner.runtimes.sidecar_art_launcher import (
    SidecarArtLauncher,
    _build_temp_daemon_config,
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


def _fake_bundle_layout(
    root: Path,
    daemon_executable: Path | None = None,
) -> SimpleNamespace:
    """Return a bundle-layout double rooted at one temp directory."""
    bin_dir = root / "bin"
    python_executable = bin_dir / "python"

    def _path_environment(current_path: str | None = None) -> str:
        if current_path:
            return f"{bin_dir}:{current_path}"
        return str(bin_dir)

    return SimpleNamespace(
        bundle_root=root,
        python_executable=python_executable,
        daemon_executable=lambda: daemon_executable,
        path_environment=_path_environment,
    )


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
    bundle_layout = _fake_bundle_layout(tmp_path)

    def process_factory(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return process

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        sidecar_art_launcher_module,
        "build_linux_bundle_layout",
        lambda: bundle_layout,
    )
    monkeypatch.setenv("PATH", "/usr/bin")

    try:
        launcher = SidecarArtLauncher(
            _settings(),
            process_factory=process_factory,
            health_opener=lambda *args, **kwargs: FakeResponse(),
            config_path_builder=lambda _settings: config_path,
            launch_preparer=lambda: None,
        )

        launcher.start()

        assert captured["command"] == [
            str(bundle_layout.python_executable),
            "-m",
            "airunner.services.daemon",
            "--config",
            str(config_path),
        ]
        environment = captured["kwargs"]["env"]
        assert captured["kwargs"]["cwd"] == str(bundle_layout.bundle_root)
        assert environment["AIRUNNER_SD_ON"] == "1"
        assert environment["AIRUNNER_LLM_ON"] == "0"
        assert environment["AIRUNNER_ART_SIDECAR_PROCESS"] == "1"
        assert environment["AIRUNNER_NO_PRELOAD"] == "1"
        assert environment["AIRUNNER_PYTHON"] == str(
            bundle_layout.python_executable
        )
        assert environment["PATH"].startswith(str(bundle_layout.python_executable.parent))
    finally:
        monkeypatch.undo()


def test_start_inherits_stdio_in_dev_mode(tmp_path, monkeypatch):
    process = FakeProcess()
    captured = {}
    config_path = tmp_path / "art-runtime.yaml"
    config_path.write_text("server: {}\n", encoding="utf-8")

    def process_factory(command, **kwargs):
        captured["kwargs"] = kwargs
        return process

    monkeypatch.setenv("DEV_ENV", "1")
    launcher = SidecarArtLauncher(
        _settings(),
        process_factory=process_factory,
        health_opener=lambda *args, **kwargs: FakeResponse(),
        config_path_builder=lambda _settings: config_path,
        launch_preparer=lambda: None,
    )

    launcher.start()

    assert captured["kwargs"]["stdout"] is None
    assert captured["kwargs"]["stderr"] is None


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
        tmp_path / "runtime" / "logs" / "art-runtime.log"
    )
    assert config["health"]["heartbeat_file"] == str(
        tmp_path / "runtime" / "art-runtime.heartbeat"
    )