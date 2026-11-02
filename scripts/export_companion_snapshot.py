#!/usr/bin/env python3
"""Make an opaque, byte-preserving copy of an explicit companion snapshot.

This is a recovery/export operation, not a database migration. It never opens
SQLite or interprets rows: every table, column, migration record, job state,
and unknown future field remains in the copied file. The operator must supply
a stable standalone backup or snapshot, never a live database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

SQLITE_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
CHUNK_SIZE = 1024 * 1024
SQLITE_HEADER = b"SQLite format 3\x00"


class SnapshotExportError(Exception):
    """Expected, content-free snapshot export failure."""


def _open_source(path: Path) -> int:
    if path.is_symlink():
        raise SnapshotExportError("source must not be a symbolic link")
    _reject_sidecars(path)
    flags = (
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SnapshotExportError("source must be an existing regular file") from exc
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise SnapshotExportError("source must be an existing regular file")
    return descriptor


def _reject_sidecars(path: Path) -> None:
    if any(
        os.path.lexists(f"{path}{suffix}")
        for suffix in SQLITE_SIDECAR_SUFFIXES
    ):
        raise SnapshotExportError(
            "source must be a standalone snapshot without SQLite sidecars"
        )


def export_snapshot(source: str | Path, destination: str | Path) -> dict[str, object]:
    """Create an exclusive copy and report only byte count and SHA-256."""
    source_path = Path(source).expanduser()
    destination_path = Path(destination).expanduser()
    if source_path.resolve(strict=False) == destination_path.resolve(strict=False):
        raise SnapshotExportError("source and destination must differ")
    try:
        source_fd = _open_source(source_path)
    except OSError as exc:
        raise SnapshotExportError("source must be an existing regular file") from exc

    destination_fd: int | None = None
    created = False
    digest = hashlib.sha256()
    byte_count = 0
    try:
        before = os.fstat(source_fd)
        header = os.read(source_fd, len(SQLITE_HEADER))
        if header != SQLITE_HEADER:
            raise SnapshotExportError("source is not a SQLite database file")
        os.lseek(source_fd, 0, os.SEEK_SET)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            destination_fd = os.open(destination_path, flags, 0o600)
            created = True
        except OSError as exc:
            raise SnapshotExportError(
                "destination must not already exist and its parent must exist"
            ) from exc

        with os.fdopen(source_fd, "rb", closefd=True) as input_file:
            source_fd = -1
            with os.fdopen(destination_fd, "wb", closefd=True) as output_file:
                destination_fd = None
                while True:
                    block = input_file.read(CHUNK_SIZE)
                    if not block:
                        break
                    output_file.write(block)
                    digest.update(block)
                    byte_count += len(block)
                output_file.flush()
                os.fsync(output_file.fileno())
            after = os.fstat(input_file.fileno())
        if _source_stat(before) != _source_stat(after):
            raise SnapshotExportError("source changed during export")
        _reject_sidecars(source_path)
        return {"bytes": byte_count, "sha256": digest.hexdigest()}
    except SnapshotExportError:
        if created:
            destination_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if created:
            destination_path.unlink(missing_ok=True)
        raise SnapshotExportError("snapshot could not be copied") from exc
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        if destination_fd is not None:
            os.close(destination_fd)


def _source_stat(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Copy an explicitly selected standalone companion snapshot. "
            "The copy contains all database content; never use a live database."
        )
    )
    parser.add_argument(
        "--source", required=True, help="stable standalone backup or snapshot"
    )
    parser.add_argument(
        "--destination", required=True, help="new local file path; must not exist"
    )
    args = parser.parse_args(argv)
    try:
        result = export_snapshot(args.source, args.destination)
    except SnapshotExportError as exc:
        print(f"snapshot export failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
