"""B14 migration-source regression tests.

Covers the migration target protocol, stable source identities,
conversation role mapping, and empty inputs. See
``test_release_b14_support`` for the shared fixtures.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine

from airunner_services.knowledge import (
    knowledge_source_identity,
    parse_knowledge_facts,
)
from airunner_services.llm.companion.migration import (
    MigrationReport,
    MigrationRequest,
    run_migration,
)
from airunner_services.llm.companion.migration_ledger import MigrationLedger
from airunner_services.llm.companion.migration_sources import (
    LegacyConversation,
    MigrationTarget,
    conversation_identity,
    legacy_conversation,
)
from test_release_b14_support import (
    BOT_PRIMARY,
    LEGACY_FILE_ONE,
    LEGACY_FILE_TWO,
    FakeTarget,
    engine,
)


def test_target_fake_satisfies_protocol() -> None:
    """The fake target is a MigrationTarget by construction."""
    assert isinstance(FakeTarget(), MigrationTarget)


def test_identities_and_parsing_are_stable() -> None:
    """Source identities and fact parsing are deterministic."""
    assert parse_knowledge_facts(LEGACY_FILE_ONE) == [
        ("Preferences", "Test user prefers tea over coffee."),
        ("Goals", "Finish the garden shed this spring."),
    ]
    assert parse_knowledge_facts(LEGACY_FILE_TWO) == [
        ("Notes", "A plain observation without a bullet.")
    ]
    assert (
        knowledge_source_identity("", "2024-05-01.md")
        == "knowledge-file:legacy:2024-05-01"
    )
    assert (
        knowledge_source_identity("tenant-a", "2024-05-01.md")
        == "knowledge-file:tenant-a:2024-05-01"
    )
    assert conversation_identity(7) == "conversation:7"


def _messy_conversation() -> LegacyConversation:
    """One legacy conversation mixing valid and malformed entries."""
    return legacy_conversation(
        21,
        int(BOT_PRIMARY),
        [
            {"is_bot": False, "content": "First"},
            {"is_bot": True, "content": "Second"},
            {"is_bot": True, "content": "   "},
            {"is_bot": False},
            "not-a-dict",
            {"is_bot": True, "content": None},
        ],
    )


def test_conversation_roles_and_id_preservation(engine: Engine) -> None:
    """Roles map from is_bot; malformed entries are skipped safely."""
    target = FakeTarget()
    messy = _messy_conversation()
    assert [m.role for m in messy.messages] == ["user", "assistant"]
    request = MigrationRequest(
        conversations=(messy,),
        known_chatbots=frozenset({int(BOT_PRIMARY)}),
    )
    report = run_migration(request, engine=engine, target=target)
    assert (report.conversations_migrated, report.turns_migrated) == (1, 2)
    assert [t.content for t in target.turns] == ["First", "Second"]
    entry = MigrationLedger(engine).entry_for("conversation:21")
    assert entry is not None
    assert entry.chatbot_id == int(BOT_PRIMARY)


def test_empty_sources_migrate_cleanly(engine: Engine, tmp_path: Path) -> None:
    """Missing roots and empty inputs migrate to a zero report."""
    report = run_migration(
        MigrationRequest(knowledge_root=tmp_path / "absent"),
        engine=engine,
        target=FakeTarget(),
    )
    assert report == MigrationReport()
