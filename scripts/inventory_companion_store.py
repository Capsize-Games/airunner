#!/usr/bin/env python3
"""Read aggregate companion-table counts from one explicit SQLite file."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import quote

EXPECTED_TABLES = (
    "companion_sessions",
    "companion_turns",
    "companion_facts",
    "companion_narratives",
    "companion_jobs",
    "companion_migration_ledger",
)
JOB_STATUSES = ("queued", "leased", "succeeded", "failed", "cancelled")
LEDGER_STATUSES = ("migrated", "failed", "needs_resolution", "resolved")
VALID_REVISION = re.compile(r"[0-9a-fA-F]{12,40}\Z")
MAX_TIMEOUT_SECONDS = 10.0
MIN_TIMEOUT_SECONDS = 0.05
BUSY_TIMEOUT_SECONDS = 0.02
PROGRESS_INSTRUCTIONS = 500
SQLITE_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")


class InventoryError(Exception):
    """Expected, content-free inventory failure."""


class InventoryDeadline:
    """Wall-clock deadline shared by all SQLite queries in one scan."""

    def __init__(self, timeout_seconds: float) -> None:
        self._end = time.monotonic() + timeout_seconds

    def expired(self) -> bool:
        return time.monotonic() >= self._end

    def check(self) -> None:
        if self.expired():
            raise InventoryError("inventory deadline exceeded")

    def progress(self) -> int:
        """Return SQLite's interrupt signal once the scan deadline passes."""
        return int(self.expired())


def _existing_database_path(raw_path: str | Path) -> Path:
    """Resolve a regular database file without following a leaf link."""
    requested = Path(raw_path).expanduser()
    try:
        if requested.is_symlink():
            raise InventoryError("database path must not be a symbolic link")
        resolved = requested.resolve(strict=True)
        if not resolved.is_file():
            raise InventoryError(
                "database path must be an existing regular file"
            )
    except (OSError, RuntimeError, ValueError) as exc:
        raise InventoryError(
            "database path must be an existing regular file"
        ) from exc
    return resolved


def _reject_sqlite_sidecars(path: Path) -> None:
    """Require a standalone snapshot with no adjacent SQLite journal files."""
    if any(
        os.path.lexists(f"{path}{suffix}")
        for suffix in SQLITE_SIDECAR_SUFFIXES
    ):
        raise InventoryError(
            "database must be a standalone snapshot without SQLite sidecars"
        )


def _execute(
    connection: sqlite3.Connection,
    deadline: InventoryDeadline,
    statement: str,
    parameters: tuple[object, ...] = (),
) -> sqlite3.Cursor:
    """Run one fixed query and translate deadline cancellation safely."""
    deadline.check()
    try:
        return connection.execute(statement, parameters)
    except sqlite3.OperationalError as exc:
        if deadline.expired():
            raise InventoryError("inventory deadline exceeded") from exc
        raise


def _status_counts(
    connection: sqlite3.Connection,
    deadline: InventoryDeadline,
    table: str,
    statuses: tuple[str, ...],
) -> dict[str, int] | None:
    """Aggregate known statuses and all other values without returning them."""
    columns = {
        str(row[1])
        for row in _execute(
            connection, deadline, f'PRAGMA table_info("{table}")'
        ).fetchall()
    }
    if "status" not in columns:
        return None

    columns_sql = ", ".join(
        "COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0)"
        for _ in statuses
    )
    placeholders = ", ".join("?" for _ in statuses)
    statement = (
        f'SELECT {columns_sql}, '
        "COALESCE(SUM(CASE WHEN status IS NULL "
        f"OR status NOT IN ({placeholders}) THEN 1 ELSE 0 END), 0) "
        f'FROM "{table}"'
    )
    row = _execute(
        connection,
        deadline,
        statement,
        tuple(statuses) + tuple(statuses),
    ).fetchone()
    return {
        **{status: int(row[index]) for index, status in enumerate(statuses)},
        "unknown": int(row[len(statuses)]),
    }


def _alembic_revision(
    connection: sqlite3.Connection,
    deadline: InventoryDeadline,
    tables: set[str],
) -> str | None:
    """Return one hex Alembic revision, or None if absent or malformed."""
    if "alembic_version" not in tables:
        return None
    columns = {
        str(row[1])
        for row in _execute(
            connection, deadline, 'PRAGMA table_info("alembic_version")'
        ).fetchall()
    }
    if "version_num" not in columns:
        return None
    rows = _execute(
        connection,
        deadline,
        'SELECT version_num FROM "alembic_version" LIMIT 2',
    ).fetchall()
    if len(rows) != 1 or not isinstance(rows[0][0], str):
        return None
    revision = rows[0][0]
    return revision.lower() if VALID_REVISION.fullmatch(revision) else None


def inventory_database(
    database: str | Path, timeout_seconds: float = 2.0
) -> dict[str, object]:
    """Return companion row counts, status aggregates, and safe revision."""
    if not MIN_TIMEOUT_SECONDS <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise InventoryError(
            f"timeout must be between {MIN_TIMEOUT_SECONDS} and "
            f"{MAX_TIMEOUT_SECONDS} seconds"
        )
    path = _existing_database_path(database)
    _reject_sqlite_sidecars(path)
    deadline = InventoryDeadline(timeout_seconds)
    uri = f"file:{quote(str(path), safe='/:')}?mode=ro&immutable=1"
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            uri,
            uri=True,
            timeout=min(BUSY_TIMEOUT_SECONDS, timeout_seconds),
        )
        connection.execute("PRAGMA query_only=ON")
        connection.set_progress_handler(
            deadline.progress, PROGRESS_INSTRUCTIONS
        )
        connection.execute("BEGIN")

        tables = {
            str(row[0])
            for row in _execute(
                connection,
                deadline,
                "SELECT name FROM sqlite_master WHERE type = 'table'",
            ).fetchall()
        }
        table_counts: dict[str, int | None] = {
            name: None for name in EXPECTED_TABLES
        }
        for table in EXPECTED_TABLES:
            if table in tables:
                row = _execute(
                    connection,
                    deadline,
                    f'SELECT COUNT(*) FROM "{table}"',
                ).fetchone()
                table_counts[table] = int(row[0])

        job_status_counts = (
            _status_counts(
                connection, deadline, "companion_jobs", JOB_STATUSES
            )
            if "companion_jobs" in tables
            else None
        )
        ledger_status_counts = (
            _status_counts(
                connection,
                deadline,
                "companion_migration_ledger",
                LEDGER_STATUSES,
            )
            if "companion_migration_ledger" in tables
            else None
        )
        revision = _alembic_revision(connection, deadline, tables)
        deadline.check()
        return {
            "table_counts": table_counts,
            "job_status_counts": job_status_counts,
            "ledger_status_counts": ledger_status_counts,
            "alembic_revision": revision,
        }
    except InventoryError:
        raise
    except sqlite3.OperationalError as exc:
        if deadline.expired():
            raise InventoryError("inventory deadline exceeded") from exc
        raise InventoryError("database could not be read as SQLite") from exc
    except sqlite3.DatabaseError as exc:
        raise InventoryError("database could not be read as SQLite") from exc
    except OSError as exc:
        raise InventoryError("database is unavailable") from exc
    finally:
        if connection is not None:
            try:
                if connection.in_transaction:
                    connection.rollback()
            finally:
                connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read aggregate counts from an explicitly selected standalone "
            "SQLite snapshot. Never use an active database."
        )
    )
    parser.add_argument(
        "--database",
        required=True,
        help="existing standalone SQLite backup or snapshot (not active)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=2.0,
        help="bounded query deadline (0.05 to 10 seconds; default: 2)",
    )
    args = parser.parse_args(argv)
    try:
        inventory = inventory_database(args.database, args.timeout_seconds)
    except InventoryError as exc:
        print(f"inventory failed: {exc}", file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error):
        print("inventory failed: database could not be read", file=sys.stderr)
        return 2
    print(json.dumps(inventory, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
