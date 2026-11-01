"""Read-only inventory checks over temporary SQLite databases only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/inventory_companion_store.py"
)
SPEC = importlib.util.spec_from_file_location("companion_inventory", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)


class CompanionStoreInventoryTests(unittest.TestCase):
    def run_cli(
        self, database: Path, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(
            prefix="companion-inventory-home-"
        ) as home:
            return subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    str(SCRIPT),
                    "--database",
                    str(database),
                    *arguments,
                ],
                env={"HOME": home, "PATH": os.defpath},
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )

    @staticmethod
    def create_fixture(path: Path, *, revision: str = "a1b2c3d4e5f6") -> None:
        sentinel = "SECRET_SENTINEL_MUST_NOT_APPEAR"
        with sqlite3.connect(path) as connection:
            connection.executescript(
                """
                CREATE TABLE companion_sessions (
                    id INTEGER, private_note TEXT
                );
                CREATE TABLE companion_turns (id INTEGER, content TEXT);
                CREATE TABLE companion_facts (id INTEGER, content TEXT);
                CREATE TABLE companion_narratives (id INTEGER, content TEXT);
                CREATE TABLE companion_jobs (
                    id INTEGER, status TEXT, payload TEXT
                );
                CREATE TABLE companion_migration_ledger (
                    id INTEGER, status TEXT, source_identity TEXT, error TEXT
                );
                CREATE TABLE alembic_version (version_num TEXT);
                """
            )
            connection.execute(
                "INSERT INTO companion_sessions VALUES (1, ?)", (sentinel,)
            )
            connection.execute(
                "INSERT INTO companion_turns VALUES (1, ?)", (sentinel,)
            )
            connection.execute(
                "INSERT INTO companion_facts VALUES (1, ?)", (sentinel,)
            )
            connection.executemany(
                "INSERT INTO companion_jobs VALUES (?, ?, ?)",
                [
                    (index, status, sentinel)
                    for index, status in enumerate(
                        (
                            "queued",
                            "leased",
                            "succeeded",
                            "failed",
                            "cancelled",
                            sentinel,
                        ),
                        start=1,
                    )
                ],
            )
            connection.executemany(
                "INSERT INTO companion_migration_ledger "
                "VALUES (?, ?, ?, ?)",
                [
                    (index, status, sentinel, sentinel)
                    for index, status in enumerate(
                        (
                            "migrated",
                            "failed",
                            "needs_resolution",
                            "resolved",
                            sentinel,
                        ),
                        start=1,
                    )
                ],
            )
            connection.execute(
                "INSERT INTO alembic_version VALUES (?)", (revision,)
            )

    def test_reports_occupancy_aggregates_and_valid_revision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "SECRET_PATH_SENTINEL.sqlite"
            self.create_fixture(database)
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            before_files = {path.name for path in Path(directory).iterdir()}

            result = self.run_cli(database)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            report = json.loads(result.stdout)
            self.assertEqual(
                report["table_counts"],
                {
                    "companion_sessions": 1,
                    "companion_turns": 1,
                    "companion_facts": 1,
                    "companion_narratives": 0,
                    "companion_jobs": 6,
                    "companion_migration_ledger": 5,
                },
            )
            self.assertEqual(
                report["job_status_counts"],
                {
                    "queued": 1,
                    "leased": 1,
                    "succeeded": 1,
                    "failed": 1,
                    "cancelled": 1,
                    "unknown": 1,
                },
            )
            self.assertEqual(
                report["ledger_status_counts"],
                {
                    "migrated": 1,
                    "failed": 1,
                    "needs_resolution": 1,
                    "resolved": 1,
                    "unknown": 1,
                },
            )
            self.assertEqual(report["alembic_revision"], "a1b2c3d4e5f6")
            self.assertNotIn("SECRET_SENTINEL", result.stdout)
            self.assertNotIn("SECRET_PATH_SENTINEL", result.stdout)
            self.assertEqual(
                hashlib.sha256(database.read_bytes()).hexdigest(), before
            )
            self.assertEqual(
                {path.name for path in Path(directory).iterdir()}, before_files
            )

    def test_invalid_revision_and_unknown_values_are_not_echoed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "inventory.sqlite"
            self.create_fixture(database, revision="SECRET_INVALID_REVISION")

            result = self.run_cli(database)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertIsNone(report["alembic_revision"])
            self.assertEqual(report["job_status_counts"]["unknown"], 1)
            self.assertEqual(report["ledger_status_counts"]["unknown"], 1)
            self.assertNotIn("SECRET_", result.stdout)

    def test_missing_path_is_not_created_or_echoed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "MISSING_PATH_SENTINEL.sqlite"

            result = self.run_cli(database)

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(database.exists())
            self.assertEqual(result.stdout, "")
            self.assertNotIn("MISSING_PATH_SENTINEL", result.stderr)

    def test_database_argument_is_required(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="companion-inventory-home-"
        ) as home:
            result = subprocess.run(
                [sys.executable, "-I", "-S", str(SCRIPT)],
                env={"HOME": home, "PATH": os.defpath},
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("--database", result.stderr)

    def test_absent_tables_are_distinct_from_empty_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "partial.sqlite"
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "CREATE TABLE companion_jobs (status TEXT)"
                )

            result = self.run_cli(database)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertIsNone(report["table_counts"]["companion_sessions"])
            self.assertEqual(report["table_counts"]["companion_jobs"], 0)
            self.assertEqual(
                report["job_status_counts"],
                {
                    "queued": 0,
                    "leased": 0,
                    "succeeded": 0,
                    "failed": 0,
                    "cancelled": 0,
                    "unknown": 0,
                },
            )
            self.assertIsNone(report["ledger_status_counts"])
            self.assertIsNone(report["alembic_revision"])

    def test_symbolic_link_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.sqlite"
            self.create_fixture(target)
            link = Path(directory) / "link.sqlite"
            link.symlink_to(target)

            result = self.run_cli(link)

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("link.sqlite", result.stderr)

    def test_progress_handler_cancels_a_long_read(self) -> None:
        connection = sqlite3.connect(":memory:")
        deadline = INVENTORY.InventoryDeadline(0.01)
        connection.set_progress_handler(deadline.progress, 100)
        try:
            with self.assertRaises(INVENTORY.InventoryError) as error:
                INVENTORY._execute(
                    connection,
                    deadline,
                    """
                    WITH RECURSIVE sequence(value) AS (
                        VALUES (0)
                        UNION ALL
                        SELECT value + 1 FROM sequence
                        WHERE value < 100000000
                    )
                    SELECT SUM(value) FROM sequence
                    """,
                ).fetchone()
            self.assertEqual(
                str(error.exception), "inventory deadline exceeded"
            )
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
