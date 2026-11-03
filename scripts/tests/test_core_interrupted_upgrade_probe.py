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


class InterruptedUpgradeProbeTests(unittest.TestCase):
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
