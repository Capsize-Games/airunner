"""The companion snapshot exporter preserves opaque SQLite files safely."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/export_companion_snapshot.py"
SPEC = importlib.util.spec_from_file_location("companion_snapshot_export", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


def _make_snapshot(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE companion_turns (id INTEGER, private_text TEXT);
            CREATE TABLE unknown_future_table (opaque BLOB);
            INSERT INTO companion_turns VALUES (8, 'SYNTHETIC_PRIVATE_FIXTURE');
            INSERT INTO unknown_future_table VALUES (x'010203');
            """
        )


def test_export_is_byte_identical_and_reports_only_hash_and_size(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.sqlite"
    destination = tmp_path / "export.sqlite"
    _make_snapshot(source)
    before = source.read_bytes()

    result = EXPORT.export_snapshot(source, destination)

    assert destination.read_bytes() == before
    assert result == {"bytes": len(before), "sha256": hashlib.sha256(before).hexdigest()}
    assert source.read_bytes() == before


def test_cli_output_contains_no_database_content(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.sqlite"
    destination = tmp_path / "export.sqlite"
    _make_snapshot(source)
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPT), "--source", str(source), "--destination", str(destination)],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
        env={"HOME": str(tmp_path), "PATH": os.defpath},
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert set(report) == {"bytes", "sha256"}
    assert "SYNTHETIC_PRIVATE_FIXTURE" not in result.stdout
    assert str(source) not in result.stdout


def test_existing_destination_is_never_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.sqlite"
    destination = tmp_path / "existing.sqlite"
    _make_snapshot(source)
    destination.write_bytes(b"keep")

    try:
        EXPORT.export_snapshot(source, destination)
    except EXPORT.SnapshotExportError as exc:
        assert "destination" in str(exc)
    else:
        raise AssertionError("existing destination was accepted")
    assert destination.read_bytes() == b"keep"


def test_rejects_same_path_symlink_and_sqlite_sidecars(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.sqlite"
    _make_snapshot(source)
    link = tmp_path / "link.sqlite"
    link.symlink_to(source)

    try:
        EXPORT.export_snapshot(source, source)
    except EXPORT.SnapshotExportError:
        pass
    else:
        raise AssertionError("same source and destination was accepted")
    try:
        EXPORT.export_snapshot(link, tmp_path / "link-copy.sqlite")
    except EXPORT.SnapshotExportError as exc:
        assert "symbolic link" in str(exc)
    else:
        raise AssertionError("symbolic-link source was accepted")

    sidecar = Path(f"{source}-wal")
    sidecar.touch()
    try:
        EXPORT.export_snapshot(source, tmp_path / "blocked.sqlite")
    except EXPORT.SnapshotExportError as exc:
        assert "sidecars" in str(exc)
    else:
        raise AssertionError("source with SQLite sidecar was accepted")
    assert not (tmp_path / "blocked.sqlite").exists()


def test_rejects_non_sqlite_source_without_creating_output(tmp_path: Path) -> None:
    source = tmp_path / "not-a-database"
    destination = tmp_path / "copy.sqlite"
    source.write_bytes(b"not a sqlite file")

    try:
        EXPORT.export_snapshot(source, destination)
    except EXPORT.SnapshotExportError as exc:
        assert "SQLite" in str(exc)
    else:
        raise AssertionError("non-SQLite source was accepted")
    assert not destination.exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX FIFO")
def test_fifo_source_is_rejected_without_waiting_for_a_writer(tmp_path: Path) -> None:
    source = tmp_path / "fifo"
    destination = tmp_path / "copy.sqlite"
    os.mkfifo(source)
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPT), "--source", str(source),
         "--destination", str(destination)],
        capture_output=True, text=True, timeout=5,
        env={"HOME": str(tmp_path), "PATH": os.defpath},
    )
    assert result.returncode == 2
    assert "regular file" in result.stderr
    assert not destination.exists()
