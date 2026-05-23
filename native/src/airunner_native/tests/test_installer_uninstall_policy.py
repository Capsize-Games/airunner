"""Regression coverage for packaged uninstall data-root behavior."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from airunner_native.repo_paths import resolve_repo_root


REPO_ROOT = resolve_repo_root(Path(__file__))
INSTALL_SCRIPT = REPO_ROOT / "install.sh"
SYSTEMD_SCRIPT = REPO_ROOT / "deployment" / "systemd" / "install.sh"
WINDOWS_INSTALLER = REPO_ROOT / "packaging" / "windows" / "airunner.nsi"


def run_script(script_path: Path, *args: str, env: dict[str, str]) -> str:
    """Run one shell helper and return combined output."""
    result = subprocess.run(
        ["bash", str(script_path), *args],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout + result.stderr


def prepare_linux_uninstall_tree(
    tmp_path: Path,
) -> tuple[dict[str, str], Path, Path, Path, Path, Path]:
    """Create one fake Linux install plus data layout for uninstall tests."""
    home_dir = tmp_path / "home"
    install_dir = tmp_path / "install"
    data_dir = tmp_path / "data"
    xdg_dir = tmp_path / "xdg"
    bin_dir = home_dir / ".local" / "bin"
    desktop_dir = xdg_dir / "applications"
    icon_dir = xdg_dir / "icons" / "hicolor" / "64x64" / "apps"

    for directory in (bin_dir, desktop_dir, icon_dir, install_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for script_name in ("airunner", "airunner-headless"):
        (bin_dir / script_name).write_text("#!/bin/sh\n", encoding="utf-8")
    (desktop_dir / "airunner.desktop").write_text("desktop\n", encoding="utf-8")
    (icon_dir / "airunner.png").write_text("icon\n", encoding="utf-8")
    (install_dir / "bundle.txt").write_text("bundle\n", encoding="utf-8")
    (data_dir / "models").mkdir(parents=True, exist_ok=True)
    (data_dir / "models" / "model.bin").write_text("model\n", encoding="utf-8")

    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home_dir),
            "XDG_DATA_HOME": str(xdg_dir),
            "AIRUNNER_INSTALL_DIR": str(install_dir),
            "AIRUNNER_DATA_DIR": str(data_dir),
        }
    )
    return env, install_dir, data_dir, bin_dir, desktop_dir, icon_dir


def test_linux_bundle_uninstall_preserves_data_by_default(tmp_path: Path) -> None:
    """Linux helper uninstall should keep the data root unless asked to purge."""
    env, install_dir, data_dir, bin_dir, desktop_dir, icon_dir = (
        prepare_linux_uninstall_tree(tmp_path)
    )

    output = run_script(INSTALL_SCRIPT, "--uninstall", env=env)

    assert not install_dir.exists()
    assert data_dir.exists()
    assert not (bin_dir / "airunner").exists()
    assert not (bin_dir / "airunner-headless").exists()
    assert not (desktop_dir / "airunner.desktop").exists()
    assert not (icon_dir / "airunner.png").exists()
    assert "user data was preserved" in output


def test_linux_bundle_uninstall_can_purge_data(tmp_path: Path) -> None:
    """Linux helper uninstall should delete the data root on explicit opt-in."""
    env, install_dir, data_dir, _, _, _ = prepare_linux_uninstall_tree(tmp_path)

    output = run_script(
        INSTALL_SCRIPT,
        "--uninstall",
        "--purge-data",
        env=env,
    )

    assert not install_dir.exists()
    assert not data_dir.exists()
    assert "Removed AIRunner data root" in output


def test_systemd_helper_help_documents_purge_data() -> None:
    """The systemd helper should expose the explicit purge-data contract."""
    output = run_script(SYSTEMD_SCRIPT, "--help", env=dict(os.environ))

    assert "--purge-data" in output
    assert "preserves user data" in output


def test_windows_uninstaller_prompts_before_purging_user_data() -> None:
    """Windows uninstall should require explicit confirmation for data purge."""
    installer_text = WINDOWS_INSTALLER.read_text(encoding="utf-8")

    assert "Also remove AIRunner user data for this Windows account?" in (
        installer_text
    )
    assert '$LOCALAPPDATA\\AIRunner' in installer_text
    assert '$APPDATA\\airunner' in installer_text
    assert '$PROFILE\\.local\\share\\airunner' in installer_text