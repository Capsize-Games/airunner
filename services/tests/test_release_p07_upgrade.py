"""P07: upgrade.sh stages/verifies before atomic activation.

Retains the previous version and rolls back app-only. Synthetic tmp
fixtures only.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from airunner_services.downloads.update_install import (
    UPGRADE_SCRIPT_ENV_VAR,
    UpdateInstallError,
    _upgrade_script_path,
)
from test_release_p07_support import _data_db
from test_release_p07_support import _rows

_UPGRADE_SH = (
    Path(__file__).resolve().parents[2] / "packaging" / "linux" / "upgrade.sh"
)


def _bundle(target: Path, version: str) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    daemon = target / "airunner-daemon"
    daemon.write_text("#!/bin/sh\necho fake\n")
    daemon.chmod(0o755)
    (target / "bundle-manifest.json").write_text("{}")
    (target / "bin").mkdir(exist_ok=True)
    (target / "legal").mkdir(exist_ok=True)
    (target / "VERSION").write_text(version)
    return target


def _installed(prefix: Path, version: str) -> Path:
    """Create versions/<version>/ with `current` pointing at it."""
    _bundle(prefix / "versions" / version, version)
    (prefix / "versions" / "current").symlink_to(version)
    return prefix


def _run(args: list[str], fail_at: str = "") -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    if fail_at:
        env["AIRUNNER_UPGRADE_FAIL_AT"] = fail_at
    return subprocess.run(
        [str(_UPGRADE_SH), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def _upgrade(
    prefix: Path, bundle: Path, fail_at: str = ""
) -> subprocess.CompletedProcess:
    return _run(["--bundle", str(bundle), "--prefix", str(prefix)], fail_at)


def _current(prefix: Path) -> str:
    return (prefix / "versions" / "current").resolve().name


def _state(prefix: Path) -> dict[str, str]:
    return json.loads((prefix / "upgrade-state.json").read_text())


def test_upgrade_activates_and_preserves_data(tmp_path: Path) -> None:
    prefix = _installed(tmp_path / "prefix", "1.2.3")
    db = prefix / "data" / "airunner.db"
    _data_db(db)
    proc = _upgrade(prefix, _bundle(tmp_path / "b", "1.2.4"))
    assert proc.returncode == 0, proc.stderr
    assert _current(prefix) == "1.2.4"
    assert (prefix / "versions" / "1.2.3").is_dir()
    assert not list((prefix / "versions").glob(".staging-*"))
    assert _state(prefix)["status"] == "ok"
    assert _state(prefix)["previous"] == "1.2.3"
    tables = "conversations app_settings media_paths policy_prefs".split()
    for table in tables:
        assert _rows(db, table) == 1
    assert (prefix / "bin" / "airunner-services").is_file()


def test_upgrade_cleans_stale_staging(tmp_path: Path) -> None:
    prefix = _installed(tmp_path / "prefix", "1.2.3")
    stale = prefix / "versions" / ".staging-9.9.9-1"
    stale.mkdir()
    (stale / "partial").write_text("interrupted copy")
    proc = _upgrade(prefix, _bundle(tmp_path / "b", "1.2.4"))
    assert proc.returncode == 0, proc.stderr
    assert not stale.exists()
    assert _current(prefix) == "1.2.4"


def test_corrupt_bundle_leaves_current_untouched(tmp_path: Path) -> None:
    prefix = _installed(tmp_path / "prefix", "1.2.3")
    bundle = tmp_path / "b"
    bundle.mkdir()
    (bundle / "VERSION").write_text("1.2.4")
    proc = _upgrade(prefix, bundle)
    assert proc.returncode != 0
    assert _current(prefix) == "1.2.3"
    assert not (prefix / "versions" / "1.2.4").exists()
    assert not list((prefix / "versions").glob(".staging-*"))


def test_interrupted_activation_recovers_on_retry(tmp_path: Path) -> None:
    prefix = _installed(tmp_path / "prefix", "1.2.3")
    bundle = _bundle(tmp_path / "b", "1.2.4")
    assert _upgrade(prefix, bundle, "activate").returncode != 0
    assert _current(prefix) == "1.2.3"
    proc = _upgrade(prefix, bundle)
    assert proc.returncode == 0, proc.stderr
    assert _current(prefix) == "1.2.4"
    assert (prefix / "versions" / "1.2.3").is_dir()
    assert _state(prefix)["status"] == "ok"


def test_rollback_restores_previous_and_keeps_data(tmp_path: Path) -> None:
    prefix = _installed(tmp_path / "prefix", "1.2.3")
    db = prefix / "data" / "airunner.db"
    _data_db(db)
    assert _upgrade(prefix, _bundle(tmp_path / "b", "1.2.4")).returncode == 0
    live = sqlite3.connect(str(db))
    live.execute("INSERT INTO conversations VALUES (2, 'after')")
    live.commit()
    live.close()
    proc = _run(["--rollback", "--prefix", str(prefix)])
    assert proc.returncode == 0, proc.stderr
    assert _current(prefix) == "1.2.3"
    assert (prefix / "versions" / "1.2.4").is_dir()
    assert _state(prefix)["status"] == "rolled-back"
    assert _rows(db, "conversations") == 2
    bad = _run(
        ["--rollback", "--prefix", str(prefix), "--rollback-to", "9.9.9"]
    )
    assert bad.returncode != 0
    assert _current(prefix) == "1.2.3"


def test_upgrade_script_override_missing_file_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A bogus installer override never becomes an executed command path."""
    monkeypatch.setenv(
        UPGRADE_SCRIPT_ENV_VAR, str(tmp_path / "no-such-upgrade.sh")
    )
    with pytest.raises(UpdateInstallError, match="does not point at a file"):
        _upgrade_script_path()


def test_upgrade_script_override_valid_file_is_honored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A real-file override resolves to that file."""
    script = tmp_path / "custom-upgrade.sh"
    script.write_text("#!/bin/sh\nexit 0\n")
    monkeypatch.setenv(UPGRADE_SCRIPT_ENV_VAR, str(script))
    assert _upgrade_script_path() == script


def test_upgrade_script_default_resolves_in_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without an override the packaged upgrade.sh is used."""
    monkeypatch.delenv(UPGRADE_SCRIPT_ENV_VAR, raising=False)
    assert _upgrade_script_path() == _UPGRADE_SH
