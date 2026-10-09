"""Migration ledger for the B14 knowledge migration.

One additive table recording, per stable source identity, whether a
legacy knowledge file or conversation migrated, failed, or waits on
an explicit ownership decision. The ledger makes reruns idempotent
and lets an interrupted migration resume: migrated sources are
skipped, failed ones are retried, and deferred ones migrate once
``resolve`` names their owner.

The caller owns the engine (production passes its database engine;
tests pass an explicit temporary SQLite engine), so this module never
touches global session state or any live database by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Connection, Engine

STATUS_MIGRATED = "migrated"
STATUS_FAILED = "failed"
STATUS_NEEDS_RESOLUTION = "needs_resolution"
STATUS_RESOLVED = "resolved"

MIGRATION_METADATA = MetaData()

MIGRATION_LEDGER_TABLE = Table(
    "companion_migration_ledger",
    MIGRATION_METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_identity", String(255), nullable=False, unique=True),
    Column("source_kind", String(64), nullable=False),
    Column("chatbot_id", Integer, nullable=True),
    Column("status", String(32), nullable=False),
    Column("target_ref", String(255), nullable=True),
    Column("checksum", String(64), nullable=True),
    Column("error", Text, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)


@dataclass(frozen=True)
class LedgerEntry:
    """One source's persisted migration outcome."""

    source_identity: str
    source_kind: str
    chatbot_id: int | None
    status: str
    target_ref: str | None
    checksum: str | None
    error: str | None


def ensure_ledger_schema(engine: Engine) -> None:
    """Create the ledger table when absent; a no-op after alembic."""
    MIGRATION_METADATA.create_all(engine, checkfirst=True)


def _find_row(
    conn: Connection, table: Table, identity: str
) -> Mapping[str, Any] | None:
    """Return one row by source identity, or None."""
    stmt = select(table).where(table.c.source_identity == identity)
    return conn.execute(stmt).mappings().first()


def _upsert_row(
    conn: Connection,
    table: Table,
    identity: str,
    values: dict[str, Any],
    now: datetime,
) -> None:
    """Update one row by identity, or insert it with a timestamp."""
    stmt = update(table).where(table.c.source_identity == identity)
    if conn.execute(stmt.values(**values)).rowcount:
        return
    conn.execute(insert(table).values(**values, created_at=now))


def _entry_from_row(row: Mapping[str, Any]) -> LedgerEntry:
    """Build one entry from a ledger result row."""
    names = (
        "source_identity",
        "source_kind",
        "chatbot_id",
        "status",
        "target_ref",
        "checksum",
        "error",
    )
    return LedgerEntry(**{name: row[name] for name in names})


class MigrationLedger:
    """Per-source migration state on a caller-owned engine."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def entry_for(self, identity: str) -> LedgerEntry | None:
        """Return one source's ledger entry, or None if unseen."""
        with self._engine.connect() as conn:
            row = _find_row(conn, MIGRATION_LEDGER_TABLE, identity)
        return None if row is None else _entry_from_row(row)

    def is_migrated(self, identity: str, checksum: str) -> bool:
        """Return True when one source needs no further work."""
        entry = self.entry_for(identity)
        return (
            entry is not None
            and entry.status == STATUS_MIGRATED
            and entry.checksum == checksum
        )

    def record_success(
        self,
        identity: str,
        kind: str,
        chatbot_id: int,
        target_ref: str,
        checksum: str,
    ) -> None:
        """Mark one source migrated to one chatbot-owned target."""
        self._store(
            identity,
            kind,
            chatbot_id,
            STATUS_MIGRATED,
            target_ref,
            checksum,
            None,
        )

    def record_failure(self, identity: str, kind: str, error: str) -> None:
        """Mark one source failed with a content-free error label."""
        self._store(identity, kind, None, STATUS_FAILED, None, None, error)

    def record_deferred(self, identity: str, kind: str, note: str) -> None:
        """Defer one source pending an explicit ownership decision."""
        self._store(
            identity,
            kind,
            None,
            STATUS_NEEDS_RESOLUTION,
            None,
            None,
            note,
        )

    def _store(
        self,
        identity: str,
        kind: str,
        chatbot_id: int | None,
        status: str,
        target_ref: str | None,
        checksum: str | None,
        error: str | None,
    ) -> None:
        """Insert one ledger row or replace it by source identity."""
        now = datetime.now(timezone.utc)
        values = {
            "source_identity": identity,
            "source_kind": kind,
            "chatbot_id": chatbot_id,
            "status": status,
            "target_ref": target_ref,
            "checksum": checksum,
            "error": error,
            "updated_at": now,
        }
        with self._engine.begin() as conn:
            _upsert_row(conn, MIGRATION_LEDGER_TABLE, identity, values, now)

    def needs_resolution(self) -> list[LedgerEntry]:
        """Return all deferred sources, oldest first."""
        table = MIGRATION_LEDGER_TABLE
        stmt = (
            select(table)
            .where(table.c.status == STATUS_NEEDS_RESOLUTION)
            .order_by(table.c.id)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [_entry_from_row(row) for row in rows]

    def resolve(self, identity: str, chatbot_id: int) -> bool:
        """Name one deferred source's owner; False if not deferred."""
        table = MIGRATION_LEDGER_TABLE
        stmt = (
            update(table)
            .where(
                table.c.source_identity == identity,
                table.c.status == STATUS_NEEDS_RESOLUTION,
            )
            .values(
                status=STATUS_RESOLVED,
                chatbot_id=chatbot_id,
                updated_at=datetime.now(timezone.utc),
            )
        )
        with self._engine.begin() as conn:
            return conn.execute(stmt).rowcount > 0

    def resolved_owner(self, identity: str) -> int | None:
        """Return one source's resolved owner, or None if unset."""
        entry = self.entry_for(identity)
        if entry is None or entry.status != STATUS_RESOLVED:
            return None
        return entry.chatbot_id


__all__ = [
    "LedgerEntry",
    "MIGRATION_LEDGER_TABLE",
    "MIGRATION_METADATA",
    "MigrationLedger",
    "STATUS_FAILED",
    "STATUS_MIGRATED",
    "STATUS_NEEDS_RESOLUTION",
    "STATUS_RESOLVED",
    "ensure_ledger_schema",
]
