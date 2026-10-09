"""B14 migration of legacy knowledge into scoped repositories.

Legacy markdown files and conversation payloads import through a
caller-supplied target, with stable per-source ledger identities
for idempotent reruns. Backs up first; originals are only read;
unknown owners defer, never silently assign.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping

from sqlalchemy.engine import Engine

from airunner_services.database.upgrade_backup import (
    BackupRecord,
    maybe_backup_before_upgrade,
)

from .contracts import ChatbotId
from .memory_repository import TurnRecord
from .migration_ledger import MigrationLedger, ensure_ledger_schema
from .migration_sources import (
    LegacyConversation,
    LegacyKnowledgeFile,
    MigratedFactRecord,
    MigrationTarget,
    scan_knowledge_directory,
    turn_call_chain_id,
)

KIND_KNOWLEDGE_FILE = "knowledge-file"
KIND_CONVERSATION = "conversation"


@dataclass(frozen=True)
class MigrationRequest:
    """Everything one migration run reads; nothing it writes."""

    knowledge_root: Path | None = None
    conversations: tuple[LegacyConversation, ...] = ()
    owner_map: Mapping[str, ChatbotId] = field(default_factory=dict)
    default_owner: ChatbotId | None = None
    known_chatbots: frozenset[int] = frozenset()


@dataclass(frozen=True)
class MigrationReport:
    """One migration run's outcome counts and backup location."""

    files_scanned: int = 0
    facts_migrated: int = 0
    conversations_migrated: int = 0
    turns_migrated: int = 0
    skipped: int = 0
    failed: int = 0
    resolutions_open: int = 0
    backup_path: str | None = None


@dataclass
class _Tally:
    """Mutable per-run counters folded into one report."""

    files_scanned: int = 0
    facts_migrated: int = 0
    conversations_migrated: int = 0
    turns_migrated: int = 0
    skipped: int = 0
    failed: int = 0

    def add(self, kind: str, count: int) -> None:
        """Add one migrated source's count to its counter."""
        if kind == KIND_KNOWLEDGE_FILE:
            self.facts_migrated += count
        else:
            self.turns_migrated += count
            self.conversations_migrated += 1

    def report(
        self, resolutions_open: int, backup: BackupRecord | None
    ) -> MigrationReport:
        """Fold these counters into one immutable report."""
        return MigrationReport(
            files_scanned=self.files_scanned,
            facts_migrated=self.facts_migrated,
            conversations_migrated=self.conversations_migrated,
            turns_migrated=self.turns_migrated,
            skipped=self.skipped,
            failed=self.failed,
            resolutions_open=resolutions_open,
            backup_path=backup.path if backup is not None else None,
        )


def run_migration(
    request: MigrationRequest,
    *,
    engine: Engine,
    target: MigrationTarget,
    db_url: str | None = None,
) -> MigrationReport:
    """Back up, then import legacy knowledge and conversations.

    The backup precedes even the ledger DDL, so it always captures
    the pre-migration database.
    """
    backup = maybe_backup_before_upgrade(db_url) if db_url else None
    ensure_ledger_schema(engine)
    ledger = MigrationLedger(engine)
    tally = _Tally()
    _migrate_files(request, ledger, target, tally)
    _migrate_conversations(request, ledger, target, tally)
    return tally.report(len(ledger.needs_resolution()), backup)


def _migrate_files(
    request: MigrationRequest,
    ledger: MigrationLedger,
    target: MigrationTarget,
    tally: _Tally,
) -> None:
    """Import one knowledge directory's facts through the ledger."""
    if request.knowledge_root is None:
        return
    for source in scan_knowledge_directory(request.knowledge_root):
        tally.files_scanned += 1
        _migrate_one_source(
            source.identity,
            source.checksum,
            KIND_KNOWLEDGE_FILE,
            source.filename,
            _file_owner(source, request, ledger),
            ledger,
            tally,
            lambda bot: _import_facts(source, bot, target),
        )


def _file_owner(
    source: LegacyKnowledgeFile,
    request: MigrationRequest,
    ledger: MigrationLedger,
) -> ChatbotId | None:
    """Return one file's explicit owner; never infer across bots."""
    if source.tenant in request.owner_map:
        return request.owner_map[source.tenant]
    if not source.tenant and request.default_owner is not None:
        return request.default_owner
    resolved = ledger.resolved_owner(source.identity)
    return ChatbotId(resolved) if resolved is not None else None


def _import_facts(
    source: LegacyKnowledgeFile, owner: ChatbotId, target: MigrationTarget
) -> tuple[int, str]:
    """Upsert one file's facts; return count and target reference."""
    for fact in source.facts:
        target.upsert_fact(
            MigratedFactRecord(
                chatbot_id=owner,
                content=fact.text,
                subject=fact.section,
                source=source.identity,
                event_id=fact.event_id,
                metadata={"filename": source.filename},
            )
        )
    return len(source.facts), f"facts:{len(source.facts)}"


def _migrate_conversations(
    request: MigrationRequest,
    ledger: MigrationLedger,
    target: MigrationTarget,
    tally: _Tally,
) -> None:
    """Import legacy conversations as chatbot-scoped turns."""
    for source in request.conversations:
        detail = f"conversation {source.conversation_id}"
        _migrate_one_source(
            source.identity,
            source.checksum,
            KIND_CONVERSATION,
            detail,
            _conversation_owner(source, request, ledger),
            ledger,
            tally,
            lambda bot: _import_turns(source, bot, target),
        )


def _conversation_owner(
    source: LegacyConversation,
    request: MigrationRequest,
    ledger: MigrationLedger,
) -> ChatbotId | None:
    """Return one conversation's owner from its stored chatbot link."""
    linked = source.chatbot_id
    if linked is not None and linked in request.known_chatbots:
        return ChatbotId(linked)
    resolved = ledger.resolved_owner(source.identity)
    return ChatbotId(resolved) if resolved is not None else None


def _import_turns(
    source: LegacyConversation, owner: ChatbotId, target: MigrationTarget
) -> tuple[int, str]:
    """Append one conversation's turns; return count and session."""
    session = target.get_or_start_session(owner)
    if session.session_id is None:
        raise ValueError("target returned a session without an id")
    for index, message in enumerate(source.messages):
        target.append_turn(
            TurnRecord(
                chatbot_id=owner,
                session_id=session.session_id,
                role=message.role,
                content=message.content,
                call_chain_id=turn_call_chain_id(source.identity, index),
            )
        )
    return len(source.messages), f"session:{session.session_id}"


def _migrate_one_source(
    identity: str,
    checksum: str,
    kind: str,
    detail: str,
    owner: ChatbotId | None,
    ledger: MigrationLedger,
    tally: _Tally,
    importer: Callable[[ChatbotId], tuple[int, str]],
) -> None:
    """Import one source idempotently or defer it with a reason."""
    if ledger.is_migrated(identity, checksum):
        tally.skipped += 1
        return
    if owner is None:
        ledger.record_deferred(identity, kind, detail)
        tally.skipped += 1
        return
    _attempt_import(ledger, tally, identity, kind, checksum, owner, importer)


def _attempt_import(
    ledger: MigrationLedger,
    tally: _Tally,
    identity: str,
    kind: str,
    checksum: str,
    owner: ChatbotId,
    importer: Callable[[ChatbotId], tuple[int, str]],
) -> None:
    """Run one source's import and ledger its outcome."""
    try:
        count, target_ref = importer(owner)
    except Exception as exc:
        ledger.record_failure(identity, kind, type(exc).__name__)
        tally.failed += 1
        return
    ledger.record_success(identity, kind, int(owner), target_ref, checksum)
    tally.add(kind, count)


__all__ = [
    "KIND_CONVERSATION",
    "KIND_KNOWLEDGE_FILE",
    "MigrationReport",
    "MigrationRequest",
    "run_migration",
]
