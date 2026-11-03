"""Subprocess regression for the CORE upgrade interruption barrier."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts/probe_core_interrupted_upgrade.py"
sys.path.insert(0, str(ROOT / "scripts"))
from probe_core_installed_interrupted_upgrade import (
    _bounded_log_snapshot,
    run_probe,
)


class InterruptedUpgradeProbeTests(unittest.TestCase):
    def test_failure_log_snapshot_is_bounded_and_redacts_credentials(self):
        with tempfile.TemporaryDirectory(prefix="core-log-snapshot-test-") as raw:
            log = Path(raw) / "interrupted.log"
            log.write_text(
                "\n".join(
                    [f"line-{index}" for index in range(100)]
                    + ["AIRUNNER_API_KEY=known-secret"]
                    + ["x" * 1500]
                ),
                encoding="utf-8",
            )

            snapshot = _bounded_log_snapshot(log, ("known-secret",))

        self.assertTrue(snapshot["available"])
        self.assertEqual(snapshot["name"], "interrupted.log")
        self.assertEqual(len(snapshot["lines"]), 80)
        self.assertLessEqual(max(map(len, snapshot["lines"])), 1000)
        self.assertTrue(any("[REDACTED]" in line for line in snapshot["lines"]))
        self.assertNotIn("known-secret", "\n".join(snapshot["lines"]))

    def test_early_frozen_exit_writes_failure_receipt_without_passing_probe(self):
        with tempfile.TemporaryDirectory(prefix="core-early-exit-test-") as raw:
            work = Path(raw)
            database = work / "fixture.db"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE marker (value TEXT)")
                connection.execute("INSERT INTO marker VALUES ('fixture')")
            digest = __import__("hashlib").sha256(database.read_bytes()).hexdigest()
            source_sha = "a" * 40
            fixture = {
                "fixture_kind": "published_prior_debian_schema",
                "database_sha256": digest,
                "source_sha": source_sha,
                "migration_source_inventory": {
                    "heads_before_candidate_upgrade": ["old-head"]
                },
            }
            fixture_record = work / "fixture.json"
            fixture_record.write_text(json.dumps(fixture), encoding="utf-8")
            expected_record = work / "expected.json"
            expected_record.write_text(
                json.dumps(
                    {
                        "source_sha": source_sha,
                        "expected_alembic_heads_after_upgrade": ["new-head"],
                    }
                ),
                encoding="utf-8",
            )
            binary = work / "airunner-core"
            binary.write_text(
                "#!/bin/sh\nprintf 'frozen-startup diagnostic sentinel\\n' >&2\nexit 7\n",
                encoding="utf-8",
            )
            binary.chmod(0o700)
            output = work / "failure-receipt.json"

            with self.assertRaisesRegex(
                RuntimeError, "exited before producing its pre-upgrade backup"
            ):
                run_probe(
                    binary,
                    database,
                    fixture_record,
                    expected_record,
                    output,
                    timeout_seconds=2,
                )

            diagnostic = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(diagnostic["status"], "failed")
            self.assertEqual(
                diagnostic["phase"], "waiting for production pre-upgrade backup"
            )
            self.assertEqual(diagnostic["interrupted_exit_code"], 7)
            self.assertIn(
                "frozen-startup diagnostic sentinel",
                "\n".join(diagnostic["interrupted_log"]["lines"]),
            )

    def test_real_setup_database_child_reaches_post_ddl_barrier(self):
        with tempfile.TemporaryDirectory(prefix="core-ddl-barrier-test-") as raw:
            work = Path(raw)
            database = work / "empty.db"
            with sqlite3.connect(database):
                pass
            base = work / "application-data"
            base.mkdir(mode=0o700)
            backup_dir = work / "backups"
            barrier = work / "barrier.json"
            db_url = f"sqlite:///{database.as_posix()}"
            pythonpath = os.pathsep.join(
                (
                    str(ROOT / "services/src"),
                    str(ROOT / "shared"),
                    str(ROOT / "debian/vendor"),
                )
            )
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(work),
                "TMPDIR": str(work),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": pythonpath,
                "HF_HUB_OFFLINE": "1",
                "HF_DATASETS_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "CUDA_VISIBLE_DEVICES": "",
            }
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(PROBE),
                    "--child",
                    "--database-url",
                    db_url,
                    "--base-path",
                    str(base),
                    "--backup-dir",
                    str(backup_dir),
                    "--barrier",
                    str(barrier),
                ],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                close_fds=True,
            )
            deadline = time.monotonic() + 60
            try:
                while time.monotonic() < deadline:
                    if barrier.is_file() or process.poll() is not None:
                        break
                    time.sleep(0.05)
                self.assertTrue(
                    barrier.is_file(),
                    f"child exited before barrier: {process.poll()}",
                )
                payload = json.loads(barrier.read_text(encoding="utf-8"))
                self.assertEqual(
                    payload["event"], "schema_ddl_after_cursor_execute"
                )
                self.assertEqual(payload["phase"], "alembic_command_upgrade")
                self.assertTrue(payload["backup_manifests_present"])
                self.assertTrue(payload["table"])
                self.assertTrue(Path(payload["setup_database_module"]).is_file())
                process.kill()
                self.assertEqual(process.wait(timeout=10), -signal.SIGKILL)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
                if process.stderr:
                    process.stderr.close()

            manifests = list(backup_dir.glob("*.db.json"))
            self.assertEqual(len(manifests), 1)
            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertTrue(Path(manifest["path"]).is_file())
            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0],
                    "ok",
                )
            with sqlite3.connect(manifest["path"]) as connection:
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0],
                    "ok",
                )


if __name__ == "__main__":
    unittest.main()
