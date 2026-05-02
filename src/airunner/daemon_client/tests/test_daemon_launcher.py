"""Tests for the GUI daemon subprocess launcher."""

from pathlib import Path
from types import SimpleNamespace

import airunner.daemon_client.daemon_launcher as daemon_launcher_module
from airunner.daemon_client.daemon_launcher import DaemonLauncher


class FakeProcess:
    """Simple subprocess double for launcher tests."""

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


class FakeRuntimeLayout:
    """Minimal runtime layout double for daemon launcher tests."""

    def __init__(self, root: Path):
        self.root = root

    def as_environment(self, config_path: Path | None) -> dict[str, str]:
        environment = {
            "AIRUNNER_RUNTIME_ROOT": str(self.root / "runtime"),
        }
        if config_path is not None:
            environment["AIRUNNER_DAEMON_CONFIG"] = str(config_path)
        return environment


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


def test_command_uses_bundle_python_module_entrypoint(
    tmp_path,
    monkeypatch,
):
    config_path = tmp_path / "daemon.yaml"
    bundle_layout = _fake_bundle_layout(tmp_path)
    monkeypatch.setattr(
        daemon_launcher_module,
        "build_linux_bundle_layout",
        lambda: bundle_layout,
    )
    launcher = DaemonLauncher(config_path=config_path)

    command = launcher.command()

    assert command == [
        str(bundle_layout.python_executable),
        "-m",
        "airunner.services.daemon",
        "--config",
        str(config_path),
    ]


def test_command_prefers_bundled_daemon_executable(tmp_path, monkeypatch):
    config_path = tmp_path / "daemon.yaml"
    daemon_executable = tmp_path / "bin" / "airunner-daemon"
    bundle_layout = _fake_bundle_layout(
        tmp_path,
        daemon_executable=daemon_executable,
    )
    monkeypatch.setattr(
        daemon_launcher_module,
        "build_linux_bundle_layout",
        lambda: bundle_layout,
    )

    launcher = DaemonLauncher(config_path=config_path)

    assert launcher.command() == [
        str(daemon_executable),
        "--config",
        str(config_path),
    ]


def test_start_spawns_process_once():
    spawned = []

    def fake_process_factory(*args, **kwargs):
        spawned.append(args[0])
        return FakeProcess()

    launcher = DaemonLauncher(process_factory=fake_process_factory)

    launcher.start()
    launcher.start()

    assert len(spawned) == 1


def test_stop_terminates_running_process():
    process = FakeProcess()
    launcher = DaemonLauncher(
        process_factory=lambda *args, **kwargs: process,
    )

    launcher.start()
    launcher.stop()

    assert process.terminated is True


def test_start_uses_configured_stdio_streams():
    spawned_kwargs = {}

    def fake_process_factory(*args, **kwargs):
        spawned_kwargs.update(kwargs)
        return FakeProcess()

    launcher = DaemonLauncher(
        process_factory=fake_process_factory,
        stdout=None,
        stderr=None,
    )

    launcher.start()

    assert spawned_kwargs["stdout"] is None
    assert spawned_kwargs["stderr"] is None


def test_start_inherits_stdio_in_dev_mode(monkeypatch):
    spawned_kwargs = {}

    def fake_process_factory(*args, **kwargs):
        spawned_kwargs.update(kwargs)
        return FakeProcess()

    monkeypatch.setenv("DEV_ENV", "1")
    launcher = DaemonLauncher(process_factory=fake_process_factory)

    launcher.start()

    assert spawned_kwargs["stdout"] is None
    assert spawned_kwargs["stderr"] is None


def test_start_defaults_bundle_context_and_headless_environment(
    tmp_path,
    monkeypatch,
):
    spawned_kwargs = {}
    config_path = tmp_path / "daemon.yaml"
    bundle_layout = _fake_bundle_layout(tmp_path)
    runtime_layout = FakeRuntimeLayout(tmp_path)

    def fake_process_factory(*args, **kwargs):
        spawned_kwargs.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(
        daemon_launcher_module,
        "build_linux_bundle_layout",
        lambda: bundle_layout,
    )
    monkeypatch.setattr(
        daemon_launcher_module,
        "build_runtime_directory_layout",
        lambda: runtime_layout,
    )
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("AIRUNNER_ART_SIDECAR_PROCESS", "1")

    launcher = DaemonLauncher(
        config_path=config_path,
        process_factory=fake_process_factory,
    )

    launcher.start()

    environment = spawned_kwargs["env"]
    assert spawned_kwargs["cwd"] == str(bundle_layout.bundle_root)
    assert environment["AIRUNNER_HEADLESS"] == "1"
    assert environment["AIRUNNER_BUNDLE_ROOT"] == str(
        bundle_layout.bundle_root
    )
    assert environment["AIRUNNER_PYTHON"] == str(
        bundle_layout.python_executable
    )
    assert environment["AIRUNNER_DAEMON_CONFIG"] == str(config_path)
    assert environment["AIRUNNER_NO_PRELOAD"] == "1"
    assert "AIRUNNER_ART_SIDECAR_PROCESS" not in environment
    assert environment["QT_QPA_PLATFORM"] == "offscreen"
    assert environment["PATH"].startswith(str(bundle_layout.python_executable.parent))


def test_start_preserves_explicit_preload_environment(tmp_path):
    spawned_kwargs = {}

    def fake_process_factory(*args, **kwargs):
        spawned_kwargs.update(kwargs)
        return FakeProcess()

    launcher = DaemonLauncher(
        process_factory=fake_process_factory,
        working_directory=tmp_path,
        environment={"AIRUNNER_NO_PRELOAD": "0"},
    )

    launcher.start()

    assert spawned_kwargs["env"]["AIRUNNER_NO_PRELOAD"] == "0"


def test_start_forwards_working_directory_and_environment(tmp_path):
    spawned_kwargs = {}

    def fake_process_factory(*args, **kwargs):
        spawned_kwargs.update(kwargs)
        return FakeProcess()

    launcher = DaemonLauncher(
        process_factory=fake_process_factory,
        working_directory=tmp_path,
        environment={"AIRUNNER_BUNDLE_ROOT": str(tmp_path)},
    )

    launcher.start()

    assert spawned_kwargs["cwd"] == str(tmp_path)
    assert spawned_kwargs["env"] == {
        "AIRUNNER_BUNDLE_ROOT": str(tmp_path),
    }