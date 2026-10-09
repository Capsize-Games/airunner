"""B14 migration-run regression tests.

Covers full migration runs: idempotent reruns, preservation of
the legacy files, failure recovery without duplicates, and the
pre-migration backup. See ``test_release_b14_support`` for the
shared fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine

from airunner_services.database.upgrade_backup import read_manifest
from airunner_services.knowledge import KnowledgeBase
from airunner_services.llm.companion.contracts import CallChainId
from airunner_services.llm.companion.migration import (
    KIND_CONVERSATION,
    KIND_KNOWLEDGE_FILE,
    MigrationReport,
    run_migration,
)
from airunner_services.llm.companion.migration_ledger import (
    MIGRATION_LEDGER_TABLE,
    STATUS_FAILED,
    STATUS_MIGRATED,
    MigrationLedger,
    ensure_ledger_schema,
)
from airunner_services.llm.companion.migration_sources import (
    MigratedFactRecord,
)
from test_release_b14_support import (
    BOT_PRIMARY,
    FakeTarget,
    _assert_files_unchanged,
    _full_request,
    _known_conversation,
    _snapshot_files,
    engine,
    knowledge_root,
)


def assert_first_full_report(first: MigrationReport) -> None:
    """Assert the first full run migrated every fixture source."""
    assert first == MigrationReport(
        files_scanned=4,
        facts_migrated=5,
        conversations_migrated=1,
        turns_migrated=2,
        skipped=0,
        failed=0,
        resolutions_open=0,
        backup_path=None,
    )


def assert_full_facts_and_turns(target: FakeTarget) -> None:
    """Assert the first run's facts, turns, and owners are exact."""
    assert all(isinstance(f, MigratedFactRecord) for f in target.facts)
    assert sorted(getattr(f, "event_id") for f in target.facts) == [
        "knowledge-file:legacy:2024-05-01#fact:0",
        "knowledge-file:legacy:2024-05-01#fact:1",
        "knowledge-file:legacy:2024-05-02#fact:0",
        "knowledge-file:tenant-a:2024-05-01#fact:0",
        "knowledge-file:tenant-unknown:2024-05-03#fact:0",
    ]
    assert [t.call_chain_id for t in target.turns] == [
        CallChainId("conversation:7#turn:0"),
        CallChainId("conversation:7#turn:1"),
    ]
    assert [t.role for t in target.turns] == ["user", "assistant"]
    assert {f.chatbot_id for f in target.facts} == {BOT_PRIMARY}


def assert_full_ledger(engine: Engine) -> None:
    """Assert the first run's ledger entries reference each write."""
    ledger = MigrationLedger(engine)
    turn_entry = ledger.entry_for("conversation:7")
    assert turn_entry is not None
    assert turn_entry.status == STATUS_MIGRATED
    assert turn_entry.source_kind == KIND_CONVERSATION
    assert turn_entry.chatbot_id == int(BOT_PRIMARY)
    assert turn_entry.target_ref == "session:1"
    file_entry = ledger.entry_for("knowledge-file:legacy:2024-05-01")
    assert file_entry is not None
    assert file_entry.source_kind == KIND_KNOWLEDGE_FILE
    assert file_entry.target_ref == "facts:2"


def assert_second_run_idempotent(
    second: MigrationReport, target: FakeTarget
) -> None:
    """Assert a rerun migrates nothing and skips every source."""
    assert second.facts_migrated == 0
    assert second.turns_migrated == 0
    assert second.skipped == 5
    assert second.failed == 0
    assert len(target.facts) == 5
    assert len(target.turns) == 2


def test_historical_fixtures_migrate_idempotently(
    knowledge_root: Path, engine: Engine
) -> None:
    """A second identical run migrates nothing new."""
    target = FakeTarget()
    request = _full_request(knowledge_root, (_known_conversation(),))
    first = run_migration(request, engine=engine, target=target)
    assert_first_full_report(first)
    assert_full_facts_and_turns(target)
    assert_full_ledger(engine)
    second = run_migration(request, engine=engine, target=target)
    assert_second_run_idempotent(second, target)


def test_original_files_preserved_and_usable(
    knowledge_root: Path, engine: Engine
) -> None:
    """Migration never modifies the legacy files it reads."""
    snapshot = _snapshot_files(knowledge_root)
    assert len(snapshot) == 4
    run_migration(
        _full_request(knowledge_root, (_known_conversation(),)),
        engine=engine,
        target=FakeTarget(),
    )
    _assert_files_unchanged(knowledge_root, snapshot)
    reader = KnowledgeBase(knowledge_dir=knowledge_root)
    assert "tea over coffee" in reader.read_file("2024-05-01")
    assert "garden shed" in reader.read_all()


def assert_failed_first_run(
    first: MigrationReport,
    engine: Engine,
    knowledge_root: Path,
    snapshot: dict[str, bytes],
) -> None:
    """Assert the failed run recorded one failure, kept data usable."""
    assert first.failed == 1
    assert first.facts_migrated == 3
    assert first.turns_migrated == 2
    ledger = MigrationLedger(engine)
    entry = ledger.entry_for("knowledge-file:legacy:2024-05-01")
    assert entry is not None
    assert entry.status == STATUS_FAILED
    assert entry.error == "RuntimeError"
    _assert_files_unchanged(knowledge_root, snapshot)
    reader = KnowledgeBase(knowledge_dir=knowledge_root)
    assert "tea over coffee" in reader.read_all()


def assert_resumed_without_dupes(
    second: MigrationReport, target: FakeTarget
) -> None:
    """Assert the resumed run completed the facts without duplicates."""
    assert second.failed == 0
    assert second.facts_migrated == 2
    assert len(target.facts) == 5
    events = [getattr(f, "event_id") for f in target.facts]
    assert len(set(events)) == 5


def test_failure_recovery_leaves_old_data_usable(
    knowledge_root: Path, engine: Engine
) -> None:
    """A failed source is recorded; resume completes without dupes."""
    snapshot = _snapshot_files(knowledge_root)
    target = FakeTarget()
    target.fail_on_upsert = 1
    request = _full_request(knowledge_root, (_known_conversation(),))
    first = run_migration(request, engine=engine, target=target)
    assert_failed_first_run(first, engine, knowledge_root, snapshot)
    second = run_migration(request, engine=engine, target=target)
    assert_resumed_without_dupes(second, target)


def prepare_backup_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: Engine
) -> None:
    """Point backups at tmp and ensure the ledger schema exists."""
    monkeypatch.setenv(
        "AIRUNNER_UPGRADE_BACKUP_DIR", str(tmp_path / "backups")
    )
    ensure_ledger_schema(engine)


def assert_backup_manifest(report: MigrationReport) -> Path:
    """Assert the report points at a real backup plus its manifest."""
    assert report.backup_path is not None
    backup_file = Path(report.backup_path)
    assert backup_file.is_file()
    manifest = backup_file.with_suffix(backup_file.suffix + ".json")
    record = read_manifest(manifest)
    assert record.path == report.backup_path
    return backup_file


def assert_backup_holds_pre_migration_db(backup_file: Path) -> None:
    """Assert the backup holds the pre-migration (empty) ledger."""
    backup_engine = create_engine(f"sqlite:///{backup_file}")
    try:
        with backup_engine.connect() as conn:
            backed_up = conn.execute(select(MIGRATION_LEDGER_TABLE)).all()
    finally:
        backup_engine.dispose()
    assert backed_up == []


def assert_live_ledger_migrated(engine: Engine) -> None:
    """Assert the live ledger holds migrated entries, no pendings."""
    live = MigrationLedger(engine)
    assert len(live.needs_resolution()) == 0
    assert live.entry_for("knowledge-file:legacy:2024-05-01") is not None


def test_backup_created_before_changes(
    knowledge_root: Path,
    engine: Engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pre-migration database is snapshotted before any write."""
    prepare_backup_run(tmp_path, monkeypatch, engine)
    report = run_migration(
        _full_request(knowledge_root, ()),
        engine=engine,
        target=FakeTarget(),
        db_url=str(engine.url),
    )
    backup_file = assert_backup_manifest(report)
    assert_backup_holds_pre_migration_db(backup_file)
    assert_live_ledger_migrated(engine)
