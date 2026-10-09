"""P07: upgrade_backup snapshots SQLite and setup_database hooks in.

Refuses to downgrade a migrated database; setup_database backs up
before migrating. Synthetic tmp fixtures only.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from airunner_services.database import upgrade_backup
from airunner_services.database.setup_database import setup_database
from airunner_services.database.upgrade_backup import (
    UpgradeBackupError,
    backup_database_for_upgrade,
    plan_recovery,
    prune_backups,
    read_manifest,
    restore_backup,
)
from test_release_p07_support import _HEAD_A
from test_release_p07_support import _HEAD_B
from test_release_p07_support import _data_db
from test_release_p07_support import _rows


def _patch_upgrade_env(
    monkeypatch: pytest.MonkeyPatch,
    live: Path,
    backups: Path,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", f"sqlite:///{live}")
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    monkeypatch.setenv("AIRUNNER_UPGRADE_BACKUP_DIR", str(backups))
    monkeypatch.setattr(upgrade_backup, "current_heads", lambda _u: (_HEAD_A,))
    real_mod = sys.modules["airunner_services.database.setup_database"]
    monkeypatch.setattr(
        real_mod,
        "_migration_heads_cache_path",
        lambda: tmp_path / "heads.json",
    )


def test_backup_round_trip_preserves_rows(tmp_path: Path) -> None:
    live = tmp_path / "data" / "airunner.db"
    _data_db(live)
    url = f"sqlite:///{live}"
    record = backup_database_for_upgrade(url, tmp_path / "backups")
    assert record is not None and record.heads == (_HEAD_A,)
    assert read_manifest(Path(record.path + ".json")) == record
    db = sqlite3.connect(str(live))
    db.execute("DELETE FROM conversations")
    db.commit()
    db.close()
    restore_backup(record, url)
    assert _rows(live, "conversations") == 1
    assert _rows(live, "policy_prefs") == 1


def test_recovery_plan_refuses_migrated_database(tmp_path: Path) -> None:
    live = tmp_path / "data" / "airunner.db"
    _data_db(live)
    url = f"sqlite:///{live}"
    record = backup_database_for_upgrade(url, tmp_path / "backups")
    assert record is not None
    db = sqlite3.connect(str(live))
    db.execute("UPDATE alembic_version SET version_num=?", (_HEAD_B,))
    db.execute("INSERT INTO conversations VALUES (9, 'new')")
    db.commit()
    db.close()
    plan = plan_recovery(url, record)
    assert plan.allow_database_restore is False
    with pytest.raises(UpgradeBackupError, match="refusing"):
        restore_backup(record, url)
    assert _rows(live, "conversations") == 2


def test_restore_refuses_tampered_backup(tmp_path: Path) -> None:
    live = tmp_path / "data" / "airunner.db"
    _data_db(live)
    url = f"sqlite:///{live}"
    record = backup_database_for_upgrade(url, tmp_path / "backups")
    assert record is not None
    with Path(record.path).open("r+b") as handle:
        handle.seek(64)
        handle.write(b"TAMPERED")
    with pytest.raises(UpgradeBackupError, match="mismatch"):
        restore_backup(record, url)
    assert _rows(live, "conversations") == 1


def test_failed_migration_leaves_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live = tmp_path / "data" / "airunner.db"
    _data_db(live)
    backups = tmp_path / "backups"
    _patch_upgrade_env(monkeypatch, live, backups, tmp_path)

    def _boom(_cfg: object, _rev: str) -> None:
        raise RuntimeError("synthetic migration failure")

    monkeypatch.setattr("alembic.command.upgrade", _boom)
    with pytest.raises(RuntimeError, match="synthetic migration failure"):
        setup_database()
    assert len(list(backups.glob("*.db.json"))) == 1
    assert _rows(live, "conversations") == 1


def test_missing_file_skipped_and_prune(tmp_path: Path) -> None:
    missing = tmp_path / "data" / "absent.db"
    assert (
        backup_database_for_upgrade(f"sqlite:///{missing}", tmp_path / "b")
        is None
    )
    live = tmp_path / "data" / "airunner.db"
    _data_db(live)
    url = f"sqlite:///{live}"
    backups = tmp_path / "backups"
    for _ in range(3):
        assert backup_database_for_upgrade(url, backups) is not None
    assert len(prune_backups(backups, 2)) == 2
    assert len(list(backups.glob("*.db"))) == 2
    with pytest.raises(UpgradeBackupError):
        backup_database_for_upgrade("postgresql://x/y", backups)
