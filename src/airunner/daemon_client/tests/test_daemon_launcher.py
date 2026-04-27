"""Tests for the GUI daemon subprocess launcher."""

from pathlib import Path

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


def test_command_uses_python_module_entrypoint(tmp_path):
    config_path = tmp_path / "daemon.yaml"
    launcher = DaemonLauncher(config_path=config_path)

    command = launcher.command()

    assert command[-4:] == [
        "-m",
        "airunner.services.daemon",
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