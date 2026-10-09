"""P06 regression: user-level Linux installer over a fixture bundle.

Covers versioned layout, repeatability, data separation, safe refusals,
launcher resolution, menu entry/icon, and the owner manual. CPU-only:
the fixture daemon echoes its environment. No GUI/model/network/DB.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LINUX_DIR = REPO_ROOT / "packaging" / "linux"
INSTALL_SH = LINUX_DIR / "install.sh"
LAUNCHER_TPL = LINUX_DIR / "airunner-services-launcher.sh"
MANUAL = LINUX_DIR / "MANUAL_INSTALL.md"
FAKE_ICON = b"fake-png-bytes-for-p06\n"


def _write_fake_bundle(bundle: Path) -> None:
    """Create a minimal structural P05 bundle with an echoing daemon."""
    for sub in ("bin", "legal", "share/icons"):
        (bundle / sub).mkdir(parents=True)
    (bundle / "bundle-manifest.json").write_text("{}\n", encoding="utf-8")
    (bundle / "VERSION").write_text("9.9.9-test\n", encoding="utf-8")
    (bundle / "legal" / "LICENSE").write_text("fixture\n", encoding="utf-8")
    icon = bundle / "share" / "icons" / "airunner-services.png"
    icon.write_bytes(FAKE_ICON)
    daemon = bundle / "airunner-daemon"
    daemon.write_text(
        '#!/bin/sh\nprintf "root=%s data=%s args=%s\\n" '
        '"$AIRUNNER_BUNDLE_ROOT" "$AIRUNNER_DATA_DIR" "$*"\n',
        encoding="utf-8",
    )
    daemon.chmod(0o755)


@pytest.fixture()
def dirs(tmp_path: Path) -> dict[str, Path]:
    """Case dirs with spaces; work/ is the unrelated working directory."""
    root = tmp_path / "case dir"
    (root / "bundle dir").mkdir(parents=True)
    _write_fake_bundle(root / "bundle dir")
    (root / "work dir").mkdir()
    (root / "canary.txt").write_text("untouched\n", encoding="utf-8")
    return {
        "bundle": root / "bundle dir",
        "prefix": root / "prefix dir",
        "xdg": root / "xdg dir",
        "work": root / "work dir",
        "canary": root / "canary.txt",
    }


def _install(
    dirs: dict[str, Path],
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Install the fixture bundle from the unrelated work directory."""
    env = dict(os.environ)
    env["XDG_DATA_HOME"] = str(dirs["xdg"])
    env.update(extra_env or {})
    return subprocess.run(
        [
            str(INSTALL_SH),
            "--bundle",
            str(dirs["bundle"]),
            "--prefix",
            str(dirs["prefix"]),
            *args,
        ],
        capture_output=True,
        text=True,
        cwd=dirs["work"],
        env=env,
        check=False,
    )


def _desktop_value(path: Path, key: str) -> str:
    """Return one KEY=value line from a desktop entry file."""
    prefix = f"{key}="
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    raise AssertionError(f"{key} missing from {path}")


def test_install_creates_versioned_layout(dirs: dict[str, Path]) -> None:
    """Happy path works with spaces in paths and an unrelated CWD."""
    proc = _install(dirs, "--version", "1.2.3")
    assert proc.returncode == 0, proc.stderr
    app = dirs["prefix"] / "versions" / "1.2.3"
    assert os.access(app / "airunner-daemon", os.X_OK)
    assert (app / "bundle-manifest.json").is_file()
    assert (app / "bin").is_dir()
    assert os.access(dirs["prefix"] / "bin" / "airunner-services", os.X_OK)
    data = dirs["prefix"] / "data"
    assert data.is_dir() and not data.is_relative_to(app)
    assert "installed airunner-services 1.2.3" in proc.stdout
    assert dirs["canary"].read_text(encoding="utf-8") == "untouched\n"


def test_reinstall_preserves_data(dirs: dict[str, Path]) -> None:
    """Reinstall replaces the version dir but keeps user data."""
    assert _install(dirs, "--version", "1.2.3").returncode == 0
    app = dirs["prefix"] / "versions" / "1.2.3"
    data_file = dirs["prefix"] / "data" / "keep.db"
    data_file.write_text("user\n", encoding="utf-8")
    (app / "stale.txt").write_text("stale\n", encoding="utf-8")
    repeat = _install(dirs, "--version", "1.2.3")
    assert repeat.returncode == 0, repeat.stderr
    assert data_file.read_text(encoding="utf-8") == "user\n"
    assert not (app / "stale.txt").exists()


def test_install_refuses_system_prefix(dirs: dict[str, Path]) -> None:
    """System prefixes fail without --allow-system-prefix."""
    proc = _install(
        dirs, "--version", "1.2.3", "--prefix", "/usr/share/airunner-p06"
    )
    assert proc.returncode != 0
    assert "system prefix" in proc.stderr
    assert not Path("/usr/share/airunner-p06").exists()
    assert not (dirs["prefix"] / "versions").exists()
    assert dirs["canary"].read_text(encoding="utf-8") == "untouched\n"


@pytest.mark.parametrize(
    "version",
    ["../evil", "a/b", "", "current", ".", "..", ".hidden", "v 1"],
)
def test_refuses_unsafe_version(dirs: dict[str, Path], version: str) -> None:
    """Versions that could escape the versions dir are rejected."""
    proc = _install(dirs, "--version", version)
    assert proc.returncode != 0
    assert not (dirs["prefix"] / "versions").exists()


def test_short_disk_space_fails_before_writing(
    dirs: dict[str, Path],
) -> None:
    """Short disk space fails the install before anything is written."""
    proc = _install(
        dirs,
        "--version",
        "1.2.3",
        extra_env={"AIRUNNER_INSTALL_REQUIRED_KB": "999999999999"},
    )
    assert proc.returncode != 0
    assert "disk space" in proc.stderr
    assert not (dirs["prefix"] / "versions").exists()
    assert not (dirs["xdg"] / "applications").exists()
    assert dirs["canary"].read_text(encoding="utf-8") == "untouched\n"


def test_launcher_resolution(dirs: dict[str, Path]) -> None:
    """Launcher resolves bundle root/data and forwards arguments."""
    assert _install(dirs, "--version", "1.2.3").returncode == 0
    launcher = dirs["prefix"] / "bin" / "airunner-services"
    env = {k: v for k, v in os.environ.items() if "AIRUNNER_" not in k}
    proc = subprocess.run(
        [str(launcher), "--alpha", "b c"],
        capture_output=True,
        text=True,
        cwd=dirs["work"],
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert f"root={dirs['prefix']}/versions/current" in proc.stdout
    assert f"data={dirs['prefix']}/data" in proc.stdout
    assert "args=--alpha b c" in proc.stdout


def test_launcher_fails_cleanly_without_daemon(
    dirs: dict[str, Path],
) -> None:
    """Launcher reports a missing daemon instead of execing garbage."""
    assert _install(dirs, "--version", "1.2.3").returncode == 0
    app = dirs["prefix"] / "versions" / "1.2.3"
    (app / "airunner-daemon").unlink()
    launcher = dirs["prefix"] / "bin" / "airunner-services"
    proc = subprocess.run(
        [str(launcher)], capture_output=True, text=True, check=False
    )
    assert proc.returncode != 0
    assert "daemon is not executable" in proc.stderr


def test_desktop_entry_resolves_launcher_and_icon(
    dirs: dict[str, Path],
) -> None:
    """Menu entry Exec points at the launcher; icon bytes installed."""
    assert _install(dirs, "--version", "1.2.3").returncode == 0
    entry = dirs["xdg"] / "applications" / "airunner-services.desktop"
    quoted = _desktop_value(entry, "Exec")
    assert quoted.startswith('"') and quoted.endswith('"')
    launcher = Path(quoted[1:-1])
    assert launcher == dirs["prefix"] / "bin" / "airunner-services"
    assert os.access(launcher, os.X_OK)
    assert _desktop_value(entry, "Icon") == "airunner-services"
    icon = dirs["xdg"] / "icons" / "hicolor" / "64x64" / "apps"
    assert (icon / "airunner-services.png").read_bytes() == FAKE_ICON


def test_version_default_and_missing_version_error(
    dirs: dict[str, Path],
) -> None:
    """VERSION file is the default; missing everywhere is an error."""
    proc = _install(dirs)
    assert proc.returncode == 0, proc.stderr
    daemon = dirs["prefix"] / "versions" / "9.9.9-test" / "airunner-daemon"
    assert daemon.is_file()
    (dirs["bundle"] / "VERSION").unlink()
    proc = _install(dirs)
    assert proc.returncode != 0
    assert "VERSION" in proc.stderr


def test_desktop_and_icon_options(dirs: dict[str, Path]) -> None:
    """--no-desktop skips entries; a missing icon warns, not fails."""
    proc = _install(dirs, "--version", "1.2.3", "--no-desktop")
    assert proc.returncode == 0, proc.stderr
    assert not (dirs["xdg"] / "applications").exists()
    icon = dirs["bundle"] / "share" / "icons" / "airunner-services.png"
    icon.unlink()
    proc = _install(dirs, "--version", "1.2.3")
    assert proc.returncode == 0, proc.stderr
    assert "fallback icon" in proc.stderr


def test_shell_entry_points() -> None:
    """Shell sources parse; --help documents the bundle flag."""
    for script in (INSTALL_SH, LAUNCHER_TPL):
        proc = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
    proc = subprocess.run(
        [str(INSTALL_SH), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--bundle DIR" in proc.stdout


def test_manual_documents_owner_install_scenario() -> None:
    """Owner scenario covers install, layout, data split, no-root."""
    text = MANUAL.read_text(encoding="utf-8").lower()
    phrases = (
        "install.sh --bundle",
        "versions/",
        "/data",
        "no root",
        "disk space",
        "menu",
    )
    for phrase in phrases:
        assert phrase in text, phrase
