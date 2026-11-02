"""Supervisors launch frozen service images without Python's -m option."""

from types import SimpleNamespace
import sys

import pytest

from airunner_services.daemon_client import launcher as daemon_launcher
from airunner_services.runtimes.sidecar_art_launcher import SidecarArtLauncher
from airunner_services.runtimes.sidecar_tts_launcher import SidecarTTSLauncher


def _launcher(kind, config, python, monkeypatch):
    layout = SimpleNamespace(
        python_executable=python, daemon_executable=lambda: None
    )
    if kind == "daemon":
        monkeypatch.setattr(daemon_launcher, "build_linux_bundle_layout", lambda: layout)
        instance = daemon_launcher.DaemonLauncher.__new__(daemon_launcher.DaemonLauncher)
        instance.config_path = config
    elif kind == "art":
        instance = SidecarArtLauncher.__new__(SidecarArtLauncher)
        instance._config_path = config
        instance._bundle_layout_builder = lambda: layout
    else:
        instance = SidecarTTSLauncher.__new__(SidecarTTSLauncher)
        instance._config_path = config
    return instance


@pytest.mark.parametrize("kind", ["daemon", "art", "tts"])
def test_frozen_launch_resolves_supervisor_alias_without_module_flag(
    kind, tmp_path, monkeypatch
):
    image = tmp_path / "airunner-core"
    image.write_text("not executed", encoding="utf-8")
    alias = tmp_path / "airunner-headless"
    alias.symlink_to(image)
    config = tmp_path / "config with spaces.yaml"
    instance = _launcher(kind, config, alias, monkeypatch)
    monkeypatch.setenv("DEV_ENV", "1")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(alias))

    assert instance.command() == [str(image), "--config", str(config)]


@pytest.mark.parametrize("kind", ["daemon", "art", "tts"])
def test_python_launch_preserves_virtual_environment_entry_point(
    kind, tmp_path, monkeypatch
):
    interpreter = tmp_path / "python3.13"
    interpreter.write_text("not executed", encoding="utf-8")
    venv_python = tmp_path / "venv-python"
    venv_python.symlink_to(interpreter)
    config = tmp_path / "config with spaces.yaml"
    instance = _launcher(kind, config, venv_python, monkeypatch)
    monkeypatch.setenv("DEV_ENV", "1")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", str(venv_python))

    assert instance.command() == [
        str(venv_python), "-m", "airunner_services.daemon", "--config", str(config)
    ]
