"""B14 ledger and ownership regression tests.

Covers unknown-owner resolution items, explicit resolve plus
resume, and the B14 ledger alembic revision. See
``test_release_b14_support`` for the shared fixtures.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from airunner_services.llm.companion.contracts import CallChainId
from airunner_services.llm.companion.migration import (
    MigrationReport,
    run_migration,
)
from airunner_services.llm.companion.migration_ledger import (
    STATUS_NEEDS_RESOLUTION,
    MigrationLedger,
)
from test_release_b14_support import (
    BOT_PRIMARY,
    BOT_SECONDARY,
    FakeTarget,
    _partial_request,
    engine,
    knowledge_root,
)

_VERSION_FILENAME = "d951d2fd378d_add_companion_migration_ledger.py"


def _load_version_module() -> ModuleType:
    """Import the B14 alembic revision file by its path."""
    versions = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "airunner_services"
        / "database"
        / "alembic"
        / "versions"
    )
    spec = importlib.util.spec_from_file_location(
        "b14_ledger_version", versions / _VERSION_FILENAME
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_version_fn(module: ModuleType, name: str, db: Engine) -> None:
    """Run one revision function against a temporary database."""
    with db.begin() as conn:
        setattr(module, "op", Operations(MigrationContext.configure(conn)))
        getattr(module, name)()


def assert_partial_report(report: MigrationReport) -> None:
    """Assert the partial run migrated only the owned sources."""
    assert report == MigrationReport(
        files_scanned=4,
        facts_migrated=1,
        conversations_migrated=1,
        turns_migrated=2,
        skipped=5,
        failed=0,
        resolutions_open=5,
        backup_path=None,
    )


def assert_pending_resolution(engine: Engine) -> None:
    """Assert the five unknown sources await explicit resolution."""
    ledger = MigrationLedger(engine)
    pending = ledger.needs_resolution()
    assert {e.source_identity for e in pending} == {
        "knowledge-file:legacy:2024-05-01",
        "knowledge-file:legacy:2024-05-02",
        "knowledge-file:tenant-unknown:2024-05-03",
        "conversation:8",
        "conversation:9",
    }
    assert {e.status for e in pending} == {STATUS_NEEDS_RESOLUTION}


def assert_partial_target_writes(target: FakeTarget) -> None:
    """Assert only the owned tenant file and known chat crossed over."""
    assert len(target.facts) == 1
    assert {f.chatbot_id for f in target.facts} == {BOT_PRIMARY}
    assert getattr(target.facts[0], "source") == (
        "knowledge-file:tenant-a:2024-05-01"
    )
    assert [t.call_chain_id for t in target.turns] == [
        CallChainId("conversation:7#turn:0"),
        CallChainId("conversation:7#turn:1"),
    ]


def test_unknown_ownership_creates_resolution_item(
    knowledge_root: Path, engine: Engine
) -> None:
    """Unknown owners defer to ledger items; nothing crosses bots."""
    target = FakeTarget()
    report = run_migration(
        _partial_request(knowledge_root),
        engine=engine,
        target=target,
    )
    assert_partial_report(report)
    assert_pending_resolution(engine)
    assert_partial_target_writes(target)


def assert_resolve_decisions(ledger: MigrationLedger) -> None:
    """Assert explicit resolutions apply; migrated sources refuse."""
    assert ledger.resolve("conversation:8", int(BOT_SECONDARY)) is True
    assert (
        ledger.resolve("knowledge-file:legacy:2024-05-01", int(BOT_PRIMARY))
        is True
    )
    assert ledger.resolve("conversation:7", int(BOT_PRIMARY)) is False


def assert_rerun_migrated(rerun: MigrationReport, target: FakeTarget) -> None:
    """Assert the rerun migrated only the newly resolved sources."""
    assert rerun.failed == 0
    assert rerun.resolutions_open == 3
    assert rerun.facts_migrated == 2
    assert rerun.turns_migrated == 2
    moved = [
        t for t in target.turns if t.call_chain_id.startswith("conversation:8")
    ]
    assert len(moved) == 2
    assert {t.chatbot_id for t in moved} == {BOT_SECONDARY}


def test_resolve_then_resume_migrates(
    knowledge_root: Path, engine: Engine
) -> None:
    """An explicit decision plus a rerun migrates deferred sources."""
    target = FakeTarget()
    request = _partial_request(knowledge_root)
    run_migration(request, engine=engine, target=target)
    ledger = MigrationLedger(engine)
    assert_resolve_decisions(ledger)
    rerun = run_migration(request, engine=engine, target=target)
    assert_rerun_migrated(rerun, target)


def ledger_column_names(engine: Engine) -> list[str]:
    """Return the ledger table's column names in upgrade order."""
    inspector = inspect(engine)
    assert "companion_migration_ledger" in inspector.get_table_names()
    return [
        column["name"]
        for column in inspector.get_columns("companion_migration_ledger")
    ]


def assert_ledger_columns(engine: Engine) -> None:
    """Assert the upgraded ledger table holds exactly its columns."""
    assert ledger_column_names(engine) == [
        "id",
        "source_identity",
        "source_kind",
        "chatbot_id",
        "status",
        "target_ref",
        "checksum",
        "error",
        "created_at",
        "updated_at",
    ]


def test_alembic_version_creates_and_drops_ledger(engine: Engine) -> None:
    """The B14 revision creates and drops exactly the ledger table."""
    module = _load_version_module()
    assert module.revision == "d951d2fd378d"
    assert module.down_revision == "3beaa16d79c8"
    _run_version_fn(module, "upgrade", engine)
    assert_ledger_columns(engine)
    _run_version_fn(module, "downgrade", engine)
    remaining = inspect(engine).get_table_names()
    assert "companion_migration_ledger" not in remaining


def test_alembic_chain_links_companion_head() -> None:
    """The B14 revision extends the companion chain without forking."""
    versions = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "airunner_services"
        / "database"
        / "alembic"
        / "versions"
    )
    names = {path.name for path in versions.glob("*.py")}
    assert _VERSION_FILENAME in names
    assert any(name.startswith("3beaa16d79c8_") for name in names)
    for path in versions.glob("*.py"):
        if path.name == _VERSION_FILENAME:
            continue
        assert "d951d2fd378d" not in path.read_text(encoding="utf-8")
