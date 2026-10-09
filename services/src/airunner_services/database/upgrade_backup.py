"""P07 SQLite backup and compatibility-aware recovery planning.

Snapshots the database before migration; permits a restore only at
identical migration heads, so a migrated database is never blindly
downgraded. Only local ``sqlite:///`` URLs are supported.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.engine import url as sa_url


class UpgradeBackupError(RuntimeError):
    """A backup cannot be taken, verified, or restored."""


@dataclass(frozen=True)
class BackupRecord:
    """Manifest describing one database backup file."""

    path: str
    sha256: str
    size_bytes: int
    heads: tuple[str, ...]
    created_utc: str
    source_url: str


@dataclass(frozen=True)
class RecoveryPlan:
    """Compatibility decision for rolling back to a backup."""

    allow_database_restore: bool
    reason: str
    backup_heads: tuple[str, ...]
    current_heads: tuple[str, ...]


def _sqlite_path(db_url: str) -> Path:
    """Return the file path for a local SQLite URL or raise."""
    parsed = sa_url.make_url(db_url)
    name = parsed.database or ""
    if parsed.drivername != "sqlite" or not name or name == ":memory:":
        raise UpgradeBackupError(f"only local sqlite URLs: {db_url}")
    return Path(name)


def _utc_stamp() -> str:
    """Return a unique UTC stamp for backup file names."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"{stamp}-{os.getpid()}Z"


def _sha256_of(path: Path) -> str:
    """Return the hex SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_heads(db_url: str) -> tuple[str, ...]:
    """Return the sorted Alembic heads recorded in one database."""
    engine = create_engine(db_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return tuple(sorted(context.get_current_heads()))
    finally:
        engine.dispose()


def write_manifest(record: BackupRecord) -> Path:
    """Persist one backup manifest sidecar; return its path."""
    payload = asdict(record)
    payload["heads"] = list(record.heads)
    backup_path = Path(record.path)
    manifest = backup_path.with_suffix(backup_path.suffix + ".json")
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest


def read_manifest(manifest: str | Path) -> BackupRecord:
    """Load and validate one backup manifest sidecar."""
    payload = json.loads(Path(manifest).read_text(encoding="utf-8"))
    heads = tuple(sorted(str(h) for h in payload.get("heads", [])))
    return BackupRecord(
        str(payload["path"]),
        str(payload["sha256"]),
        int(payload["size_bytes"]),
        heads,
        str(payload["created_utc"]),
        str(payload["source_url"]),
    )


def _snapshot_sqlite(source: Path, dest: Path) -> None:
    """Copy one SQLite file consistently via VACUUM INTO."""
    quoted = str(dest).replace("'", "''")
    connection = sqlite3.connect(str(source))
    try:
        connection.execute(f"VACUUM INTO '{quoted}'")
    finally:
        connection.close()


def _snapshot_record(db_url: str, dest: Path) -> BackupRecord:
    """Snapshot one database file and return its manifest record."""
    _snapshot_sqlite(_sqlite_path(db_url), dest)
    try:
        os.chmod(dest, 0o600)
    except OSError:
        pass
    return BackupRecord(
        str(dest),
        _sha256_of(dest),
        dest.stat().st_size,
        current_heads(db_url),
        _utc_stamp(),
        db_url,
    )


def _prepare_backup_dir(backup_dir: str | Path, stem: str) -> Path:
    """Create one backup dir and return a fresh destination path."""
    target_dir = Path(backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(target_dir, 0o700)
    except OSError:
        pass
    return target_dir / f"{stem}-{_utc_stamp()}.db"


def backup_database_for_upgrade(
    db_url: str,
    backup_dir: str | Path,
) -> BackupRecord | None:
    """Back up one SQLite database before migration.

    Returns None when the file does not exist yet (nothing to
    preserve). Raises on non-SQLite URLs and backup failures.
    """
    source = _sqlite_path(db_url)
    if not source.exists():
        return None
    dest = _prepare_backup_dir(backup_dir, source.stem)
    record = _snapshot_record(db_url, dest)
    write_manifest(record)
    return record


def default_backup_dir(db_url: str) -> str | None:
    """Return the backup dir for one URL, or None when not SQLite."""
    override = os.environ.get("AIRUNNER_UPGRADE_BACKUP_DIR")
    if override:
        return override
    if not db_url.startswith("sqlite:///"):
        return None
    parent = os.path.dirname(db_url.replace("sqlite:///", "", 1))
    return os.path.join(parent, "backups") if parent else None


def maybe_backup_before_upgrade(db_url: str) -> BackupRecord | None:
    """Snapshot one database or raise when a backup is impossible.

    Skips non-SQLite URLs (no file to snapshot) and missing files.
    """
    backup_dir = default_backup_dir(db_url)
    if backup_dir is None:
        return None
    try:
        return backup_database_for_upgrade(db_url, backup_dir)
    except UpgradeBackupError as exc:
        raise RuntimeError(f"refusing to migrate: {exc}") from exc


def plan_recovery(db_url: str, backup: BackupRecord) -> RecoveryPlan:
    """Decide whether one backup may be restored over a live database.

    Allowed only at identical heads (the upgrade never migrated the
    database). Otherwise the migrated database is kept and only the
    application rolls back.
    """
    live = current_heads(db_url)
    if live == backup.heads:
        return RecoveryPlan(True, "database unmigrated", backup.heads, live)
    return RecoveryPlan(
        False, "database migrated; keep it", backup.heads, live
    )


def _verify_backup(record: BackupRecord) -> Path:
    """Return one backup path after size/digest verification."""
    path = Path(record.path)
    if not path.is_file():
        raise UpgradeBackupError(f"backup file missing: {path}")
    if path.stat().st_size != record.size_bytes:
        raise UpgradeBackupError(f"backup size mismatch: {path}")
    if _sha256_of(path) != record.sha256:
        raise UpgradeBackupError(f"backup digest mismatch: {path}")
    return path


def restore_backup(record: BackupRecord, db_url: str) -> Path:
    """Restore one verified backup over a compatible live database.

    Refuses migrated live databases and tampered backups. Returns
    the live database path.
    """
    plan = plan_recovery(db_url, record)
    if not plan.allow_database_restore:
        raise UpgradeBackupError(f"refusing restore: {plan.reason}")
    backup_path = _verify_backup(record)
    live_path = _sqlite_path(db_url)
    live_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        Path(str(live_path) + suffix).unlink(missing_ok=True)
    _snapshot_sqlite(backup_path, live_path)
    return live_path


def prune_backups(backup_dir: str | Path, keep: int) -> list[Path]:
    """Delete all but the newest ``keep`` backups; return survivors."""
    if keep < 0:
        raise UpgradeBackupError(f"invalid keep count: {keep}")
    resolved = Path(backup_dir).resolve()
    manifests = sorted(Path(backup_dir).glob("*.db.json"))
    for manifest in manifests[: max(0, len(manifests) - keep)]:
        candidate = Path(read_manifest(manifest).path)
        if candidate.resolve().parent == resolved:
            candidate.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
    return manifests[max(0, len(manifests) - keep) :]


__all__ = [
    "BackupRecord",
    "RecoveryPlan",
    "UpgradeBackupError",
    "backup_database_for_upgrade",
    "current_heads",
    "default_backup_dir",
    "maybe_backup_before_upgrade",
    "plan_recovery",
    "prune_backups",
    "read_manifest",
    "restore_backup",
    "write_manifest",
]
