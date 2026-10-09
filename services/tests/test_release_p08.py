"""Regression tests for release issue P08 (safe uninstall).

Proves `packaging/linux/uninstall.sh` removes only installer-owned
app/launcher/menu artifacts, preserves all user data by default, and
deletes only allowlisted owned files under an explicit
`--delete-data --yes` action. Fixtures live under `tmp_path` with
spaces in paths and an unrelated working directory; the only
database is an explicit temporary SQLite file. No GUI, model,
network, or live-DB side effects.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_UNINSTALL = _REPO_ROOT / "packaging" / "linux" / "uninstall.sh"
_LAUNCHER_TMPL = _REPO_ROOT / "packaging" / "linux"
_LAUNCHER_TMPL = _LAUNCHER_TMPL / "airunner-services-launcher.sh"
_DESKTOP_TMPL = _REPO_ROOT / "packaging" / "linux"
_DESKTOP_TMPL = _DESKTOP_TMPL / "airunner-services.desktop"

_DESKTOP = "airunner-services.desktop"
_ICON = "airunner-services.png"
_OWNED = (
    "airunner.db",
    "airunner.db-journal",
    "airunner.db-shm",
    "airunner.db-wal",
    "settings.json",
    "service.log",
)
_USER_FILES = (
    "models/model.bin",
    "media/photo.png",
    "backups/airunner.db.bak",
)


def _render_launcher(data: Path, dest: Path) -> None:
    quoted = "'" + str(data).replace("'", "'\\''") + "'"
    text = _LAUNCHER_TMPL.read_text()
    text = text.replace("@AIRUNNER_DAEMON@", "airunner-daemon")
    text = text.replace("@AIRUNNER_DATA_DIR@", quoted)
    dest.write_text(text)


def _seed_data(data: Path) -> None:
    data.mkdir(parents=True)
    conn = sqlite3.connect(data / "airunner.db")
    conn.execute("CREATE TABLE note (t TEXT)")
    conn.execute("INSERT INTO note (t) VALUES ('keepme')")
    conn.commit()
    conn.close()
    for name in _OWNED:
        if name != "airunner.db":
            (data / name).write_text("managed")
    for name in _USER_FILES:
        target = data / name
        target.parent.mkdir(parents=True)
        target.write_bytes(b"user-bytes")


def _install_app(prefix: Path, data: Path) -> Path:
    version = prefix / "versions" / "1.2.3"
    (version / "bin").mkdir(parents=True)
    (version / "legal").mkdir()
    daemon = version / "airunner-daemon"
    daemon.write_text("#!/bin/sh\nexit 0\n")
    daemon.chmod(0o755)
    (version / "bundle-manifest.json").write_text("{}")
    scratch = prefix / "versions" / "notes" / "scratch.txt"
    scratch.parent.mkdir()
    scratch.write_text("user note")
    (prefix / "versions" / "current").symlink_to("1.2.3")
    launcher = prefix / "bin" / "airunner-services"
    launcher.parent.mkdir(parents=True)
    _render_launcher(data, launcher)
    launcher.chmod(0o755)
    return launcher


def _install_menu(root: Path, launcher: Path) -> Path:
    xdg = root / "xdg home"
    apps = xdg / "applications"
    apps.mkdir(parents=True)
    text = _DESKTOP_TMPL.read_text()
    text = text.replace("@AIRUNNER_LAUNCHER@", str(launcher))
    (apps / _DESKTOP).write_text(text)
    icons = xdg / "icons" / "hicolor" / "64x64" / "apps"
    icons.mkdir(parents=True)
    (icons / _ICON).write_bytes(b"\x89PNG")
    return xdg


def _install_tree(
    root: Path, custom: Path | None = None
) -> tuple[Path, Path, Path, Path]:
    prefix = root / "airunner inst"
    home = root / "home"
    home.mkdir()
    data = custom if custom is not None else prefix / "data"
    _seed_data(data)
    launcher = _install_app(prefix, data)
    xdg = _install_menu(root, launcher)
    return prefix, data, xdg, home


def _run_uninstall(
    args: list[str], root: Path, xdg: Path, home: Path
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, XDG_DATA_HOME=str(xdg), HOME=str(home))
    work = root / "elsewhere"
    work.mkdir(exist_ok=True)
    return subprocess.run(
        ["bash", str(_UNINSTALL), *args],
        capture_output=True,
        text=True,
        cwd=work,
        env=env,
        timeout=60,
    )


def _db_note(data: Path) -> str:
    conn = sqlite3.connect(data / "airunner.db")
    row = conn.execute("SELECT t FROM note").fetchone()
    conn.close()
    return str(row[0])


def test_default_uninstall_preserves_data(tmp_path: Path) -> None:
    prefix, data, xdg, home = _install_tree(tmp_path)
    proc = _run_uninstall(["--prefix", str(prefix)], tmp_path, xdg, home)
    assert proc.returncode == 0, proc.stderr
    assert not (prefix / "versions" / "1.2.3").exists()
    assert not (prefix / "versions" / "current").exists()
    assert not (prefix / "bin" / "airunner-services").exists()
    assert not (xdg / "applications" / _DESKTOP).exists()
    icon = xdg / "icons" / "hicolor" / "64x64" / "apps" / _ICON
    assert not icon.exists()
    notes = prefix / "versions" / "notes" / "scratch.txt"
    assert notes.exists()
    for name in _OWNED + _USER_FILES:
        assert (data / name).exists()
    # Read the DB last: opening it lets SQLite clean stale journals.
    assert _db_note(data) == "keepme"
    rerun = _run_uninstall(["--prefix", str(prefix)], tmp_path, xdg, home)
    assert rerun.returncode == 0, rerun.stderr


def test_delete_data_without_yes_only_shows_plan(tmp_path: Path) -> None:
    prefix, data, xdg, home = _install_tree(tmp_path)
    proc = _run_uninstall(
        ["--prefix", str(prefix), "--delete-data"], tmp_path, xdg, home
    )
    assert proc.returncode != 0
    assert "airunner.db" in proc.stdout
    assert "--yes" in proc.stderr
    assert _db_note(data) == "keepme"
    assert (data / "settings.json").exists()


def test_delete_data_removes_only_owned_files(tmp_path: Path) -> None:
    prefix, data, xdg, home = _install_tree(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("do not touch")
    (data / "service.log").unlink()
    (data / "service.log").symlink_to(outside)
    proc = _run_uninstall(
        ["--prefix", str(prefix), "--delete-data", "--yes"],
        tmp_path,
        xdg,
        home,
    )
    assert proc.returncode == 0, proc.stderr
    for name in _OWNED:
        if name == "service.log":
            assert (data / name).is_symlink()
        else:
            assert not (data / name).exists()
    assert outside.read_text() == "do not touch"
    for name in _USER_FILES:
        assert (data / name).exists()


def test_custom_data_dir_is_honored(tmp_path: Path) -> None:
    custom = tmp_path / "custom data"
    prefix, data, xdg, home = _install_tree(tmp_path, custom)
    other = tmp_path / "other data"
    _seed_data(other)
    proc = _run_uninstall(
        [
            "--prefix",
            str(prefix),
            "--data-dir",
            str(other),
            "--delete-data",
            "--yes",
        ],
        tmp_path,
        xdg,
        home,
    )
    assert proc.returncode == 0, proc.stderr
    assert not (other / "airunner.db").exists()
    assert _db_note(custom) == "keepme"
    (prefix / "bin").mkdir()
    _render_launcher(custom, prefix / "bin" / "airunner-services")
    rerun = _run_uninstall(
        ["--prefix", str(prefix), "--delete-data", "--yes"],
        tmp_path,
        xdg,
        home,
    )
    assert rerun.returncode == 0, rerun.stderr
    assert not (custom / "airunner.db").exists()
    assert (custom / "models" / "model.bin").exists()


def test_delete_data_refuses_home_and_root(tmp_path: Path) -> None:
    prefix, data, xdg, home = _install_tree(tmp_path)
    for target in (str(home), "/"):
        proc = _run_uninstall(
            [
                "--prefix",
                str(prefix),
                "--data-dir",
                target,
                "--delete-data",
                "--yes",
            ],
            tmp_path,
            xdg,
            home,
        )
        assert proc.returncode != 0
    assert _db_note(data) == "keepme"


def test_foreign_menu_entry_is_kept(tmp_path: Path) -> None:
    prefix, data, xdg, home = _install_tree(tmp_path)
    desktop = xdg / "applications" / _DESKTOP
    desktop.write_text('[Desktop Entry]\nExec="/other/bin/x"\n')
    proc = _run_uninstall(["--prefix", str(prefix)], tmp_path, xdg, home)
    assert proc.returncode == 0, proc.stderr
    assert desktop.exists()
    assert "another install" in proc.stderr


def test_system_prefix_is_refused(tmp_path: Path) -> None:
    prefix, data, xdg, home = _install_tree(tmp_path)
    proc = _run_uninstall(["--prefix", "/opt/airunner"], tmp_path, xdg, home)
    assert proc.returncode != 0
    assert "system prefix" in proc.stderr
    assert _db_note(data) == "keepme"


def test_uninstall_script_passes_syntax_check() -> None:
    proc = subprocess.run(
        ["bash", "-n", str(_UNINSTALL)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
