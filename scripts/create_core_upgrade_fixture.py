#!/usr/bin/env python3
"""Create a synthetic SQLite migration fixture for the CORE Debian workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


_REVISION = "69fb44e0d99f"
_SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")
_FIXTURE_PAYLOAD = "synthetic-core-upgrade-data-preservation-fixture-v1"


def _database_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def _configure_database_environment(database: Path, base_path: Path) -> str:
    database_url = _database_url(database)
    os.environ["AIRUNNER_DATABASE_URL"] = database_url
    os.environ["AIRUNNER_BASE_PATH"] = str(base_path)
    os.environ["AIRUNNER_DATA_DIR"] = str(base_path)
    os.environ["AIRUNNER_MIGRATION_RUNNING"] = "1"
    return database_url


def _alembic_config(database_url: str) -> tuple[Config, tuple[str, ...]]:
    database_dir = Path(__file__).resolve().parents[1] / "services/src/airunner_services/database"
    config = Config(str(database_dir / "alembic.ini"))
    config.set_main_option("script_location", str(database_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    heads = tuple(sorted(ScriptDirectory.from_config(config).get_heads()))
    if not heads:
        raise RuntimeError("CORE database migration graph has no heads")
    return config, heads


def _run_intermediate_migrations(database_url: str, base_path: Path) -> None:
    """Run Alembic in a short-lived process so its SQLite engine closes."""
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--migrate-only",
            "--database-url",
            database_url,
            "--base-path",
            str(base_path),
        ],
        check=True,
        env=os.environ.copy(),
        timeout=120,
    )


def _build_intermediate_database(database: Path) -> None:
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "CREATE TABLE core_upgrade_fixture "
            "(marker TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO core_upgrade_fixture(marker, payload) VALUES (?, ?)",
            ("synthetic-marker", _FIXTURE_PAYLOAD),
        )
        connection.commit()
        current = tuple(
            row[0]
            for row in connection.execute(
                "SELECT version_num FROM alembic_version ORDER BY version_num"
            )
        )
    finally:
        connection.close()
    if current != (_REVISION,):
        raise RuntimeError(f"fixture migration revision differs: {current!r}")


def _checkpoint_fixture_database(database: Path) -> None:
    """Make the SQLite file self-contained before recording its digest."""
    connection = sqlite3.connect(database, timeout=15)
    try:
        checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if checkpoint is not None and checkpoint[0] != 0:
            raise RuntimeError("fixture SQLite WAL checkpoint was busy")
        mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
        if mode is None or mode[0].lower() != "delete":
            raise RuntimeError("fixture SQLite journal mode did not become DELETE")
    finally:
        connection.close()
    for suffix in ("-wal", "-shm"):
        if database.with_name(database.name + suffix).exists():
            raise RuntimeError("fixture SQLite sidecar remains after checkpoint")


def create_fixture(output_dir: Path, source_sha: str) -> dict[str, object]:
    if not _SOURCE_SHA.fullmatch(source_sha):
        raise ValueError("source SHA must be a full lowercase Git commit ID")
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"fixture output already exists: {output_dir}")
    output_dir.mkdir(parents=True, mode=0o700)
    database = output_dir / "airunner.db"
    base_path = output_dir / "application-data"
    base_path.mkdir(mode=0o700)
    database_url = _configure_database_environment(database, base_path)
    config, heads = _alembic_config(database_url)
    _run_intermediate_migrations(database_url, base_path)
    _build_intermediate_database(database)
    _checkpoint_fixture_database(database)
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    record: dict[str, object] = {
        "schema_version": 1,
        "fixture_kind": "synthetic_intermediate_alembic_revision",
        "fixture_payload": _FIXTURE_PAYLOAD,
        "source_sha": source_sha,
        "database_filename": database.name,
        "database_sha256": digest,
        "alembic_revision_before_upgrade": _REVISION,
        "expected_alembic_heads_after_upgrade": list(heads),
        "limitation": (
            "Uses this source revision's migration files and is not a database "
            "or schema recovered from a previously published Debian package."
        ),
    }
    (output_dir / "fixture.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--migrate-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--database-url")
    parser.add_argument("--base-path", type=Path)
    args = parser.parse_args()
    if args.migrate_only:
        if not args.database_url or args.base_path is None:
            parser.error("--migrate-only requires --database-url and --base-path")
        os.environ["AIRUNNER_DATABASE_URL"] = args.database_url
        os.environ["AIRUNNER_BASE_PATH"] = str(args.base_path)
        os.environ["AIRUNNER_DATA_DIR"] = str(args.base_path)
        os.environ["AIRUNNER_MIGRATION_RUNNING"] = "1"
        config, _ = _alembic_config(args.database_url)
        command.upgrade(config, _REVISION)
        return 0
    if args.output_dir is None or args.source_sha is None:
        parser.error("--output-dir and --source-sha are required")
    record = create_fixture(args.output_dir, args.source_sha)
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
