"""Bounded archive and synthetic-data tests for the prior CORE schema fixture."""

from __future__ import annotations

import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import create_core_published_upgrade_fixture as fixture  # noqa: E402


class PublishedUpgradeFixtureTests(unittest.TestCase):
    def test_archive_paths_reject_absolute_and_parent_traversal(self):
        for name in ("/tmp/escape.py", "usr/lib/../../tmp/escape.py"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                fixture._canonical_member(name)

    def test_archive_sources_are_bounded_and_select_only_expected_packages(
        self,
    ):
        archive_bytes = io.BytesIO()
        migration_root = "./usr/lib/python3/dist-packages/airunner_services/database/alembic/versions/"
        required = (
            "./usr/lib/python3/dist-packages/airunner_services/__init__.py",
            "./usr/lib/python3/dist-packages/airunner_services/database/alembic.ini",
            "./usr/lib/python3/dist-packages/airunner_services/database/alembic/env.py",
            "./usr/lib/python3/dist-packages/airunner_common/__init__.py",
        )
        with tarfile.open(fileobj=archive_bytes, mode="w") as archive:
            for name in required:
                info = tarfile.TarInfo(name)
                content = b"# synthetic fixture source\n"
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
            for index in range(fixture._EXPECTED_MIGRATION_COUNT):
                revision = f"migration-{index:02d}"
                name = f"{migration_root}{revision}.py"
                info = tarfile.TarInfo(name)
                content = b"revision = 'fixture'\ndown_revision = None\n"
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
            outside = tarfile.TarInfo("./usr/share/ignored.txt")
            content = b"outside the selected Python package roots"
            outside.size = len(content)
            archive.addfile(outside, io.BytesIO(content))
        result = subprocess.CompletedProcess(
            args=["dpkg-deb", "--fsys-tarfile"],
            returncode=0,
            stdout=archive_bytes.getvalue(),
            stderr=b"",
        )
        with patch.object(fixture.subprocess, "run", return_value=result):
            sources, inventory = fixture._read_archive_sources(
                Path("baseline.deb")
            )
        self.assertEqual(len(inventory), 4 + fixture._EXPECTED_MIGRATION_COUNT)
        self.assertFalse(any(name.endswith("ignored.txt") for name in sources))
        self.assertTrue(all(item["sha256"] for item in inventory))

    def test_archive_sources_reject_selected_symlinks(self):
        archive_bytes = io.BytesIO()
        with tarfile.open(fileobj=archive_bytes, mode="w") as archive:
            link = tarfile.TarInfo(
                "./usr/lib/python3/dist-packages/airunner_services/unsafe.py"
            )
            link.type = tarfile.SYMTYPE
            link.linkname = "/tmp/unsafe.py"
            archive.addfile(link)
        result = subprocess.CompletedProcess(
            args=["dpkg-deb", "--fsys-tarfile"],
            returncode=0,
            stdout=archive_bytes.getvalue(),
            stderr=b"",
        )
        with patch.object(fixture.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(ValueError, "non-regular selected"):
                fixture._read_archive_sources(Path("baseline.deb"))

    def test_revision_graph_binds_both_published_heads(self):
        with tempfile.TemporaryDirectory(
            prefix="core-baseline-graph-"
        ) as temporary:
            package_root = Path(temporary) / "airunner_services"
            versions = package_root / "database/alembic/versions"
            versions.mkdir(parents=True)
            (versions / "f0b1f4cf8f41.py").write_text(
                "revision = 'f0b1f4cf8f41'\ndown_revision = None\n",
                encoding="utf-8",
            )
            (versions / "a7c93f2e1b4d.py").write_text(
                "revision = 'a7c93f2e1b4d'\ndown_revision = 'f0b1f4cf8f41'\n",
                encoding="utf-8",
            )
            (versions / "3beaa16d79c8.py").write_text(
                "revision = '3beaa16d79c8'\ndown_revision = None\n",
                encoding="utf-8",
            )
            (versions / "d951d2fd378d.py").write_text(
                "revision = 'd951d2fd378d'\ndown_revision = '3beaa16d79c8'\n",
                encoding="utf-8",
            )
            heads, graph_sha = fixture._migration_graph(package_root)
        self.assertEqual(heads, fixture._EXPECTED_BASELINE_HEADS)
        self.assertEqual(len(graph_sha), 64)

    def test_conversation_fixture_retains_synthetic_content(self):
        with tempfile.TemporaryDirectory(
            prefix="core-baseline-db-"
        ) as temporary:
            database = Path(temporary) / "fixture.db"
            import sqlite3

            with sqlite3.connect(database) as connection:
                connection.execute(
                    "CREATE TABLE conversations ("
                    "id INTEGER PRIMARY KEY, value TEXT NOT NULL, "
                    "chatbot_name TEXT NOT NULL, user_name TEXT NOT NULL, "
                    "title TEXT, status TEXT)"
                )
            result = fixture._insert_synthetic_data(database)
            with sqlite3.connect(database) as connection:
                row = connection.execute(
                    "SELECT id, title, value FROM conversations WHERE id=?",
                    (result["conversation_id"],),
                ).fetchone()
                marker = connection.execute(
                    "SELECT payload FROM core_upgrade_fixture WHERE marker=?",
                    ("synthetic-marker",),
                ).fetchone()
            self.assertEqual(
                row,
                (
                    result["conversation_id"],
                    result["conversation_title"],
                    result["conversation_payload"],
                ),
            )
            self.assertEqual(
                result["conversation_summary"],
                "Synthetic retained conversation summary.",
            )
            self.assertEqual(marker, (fixture._FIXTURE_PAYLOAD,))

    def test_migration_child_uses_null_keyring_and_drops_other_environment(
        self,
    ):
        with tempfile.TemporaryDirectory(
            prefix="core-baseline-child-"
        ) as temporary:
            root = Path(temporary)
            package_root = root / "airunner_services"
            package_root.mkdir()
            database = root / "fixture.db"
            data_root = root / "data"
            with patch.dict(
                os.environ, {"SECRET_SHOULD_NOT_PASS": "secret"}, clear=False
            ):
                with patch.object(fixture.subprocess, "run") as run:
                    run.return_value = subprocess.CompletedProcess(
                        [], 0, "", ""
                    )
                    fixture._run_published_migrations(
                        package_root, root, database, data_root
                    )
            kwargs = run.call_args.kwargs
            child_env = kwargs["env"]
            self.assertNotIn("SECRET_SHOULD_NOT_PASS", child_env)
            self.assertIn("PYTHONPATH", child_env)
            self.assertTrue((root / "test-null-keyring/keyring.py").is_file())
            self.assertEqual(kwargs["timeout"], 120)


if __name__ == "__main__":
    unittest.main()
