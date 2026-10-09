"""Shared fixtures and helpers for the B14 release tests.

Holds the in-memory migration target, the synthetic legacy
fixtures, and the request builders used by every
``test_release_b14_*`` module. Defines no tests itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from airunner_services.llm.companion.contracts import ChatbotId, SessionId
from airunner_services.llm.companion.memory_repository import (
    FactRecord,
    SessionRecord,
    TurnRecord,
)
from airunner_services.llm.companion.migration import MigrationRequest
from airunner_services.llm.companion.migration_sources import (
    LegacyConversation,
    legacy_conversation,
)

BOT_PRIMARY = ChatbotId(11)
BOT_SECONDARY = ChatbotId(12)

LEGACY_FILE_ONE = """# Knowledge - 2024-05-01

## Preferences

- Test user prefers tea over coffee.

## Goals

- Finish the garden shed this spring.
"""

LEGACY_FILE_TWO = """# Knowledge - 2024-05-02

## Notes

A plain observation without a bullet.
"""

TENANT_FILE = """# Knowledge - 2024-05-01

## Interests & Hobbies

- Test user enjoys landscape photography.
"""


class FakeTarget:
    """An in-memory migration target recording every write."""

    def __init__(self) -> None:
        self.facts: list[FactRecord] = []
        self.turns: list[TurnRecord] = []
        self.sessions: dict[int, SessionRecord] = {}
        self.fail_on_upsert = 0
        self.fail_on_append = 0

    def upsert_fact(self, fact: FactRecord) -> FactRecord:
        """Record one fact, failing synthetically when armed."""
        if self.fail_on_upsert:
            self.fail_on_upsert -= 1
            raise RuntimeError("synthetic fact failure")
        self.facts.append(fact)
        return fact

    def get_or_start_session(self, chatbot_id: ChatbotId) -> SessionRecord:
        """Return one stable fake session per chatbot."""
        key = int(chatbot_id)
        session = self.sessions.get(key)
        if session is None:
            session = SessionRecord(
                session_id=SessionId(len(self.sessions) + 1),
                chatbot_id=chatbot_id,
                started_at="2026-01-01T00:00:00",
                last_message_at="2026-01-01T00:00:00",
            )
            self.sessions[key] = session
        return session

    def append_turn(self, turn: TurnRecord) -> TurnRecord:
        """Record one turn, failing synthetically when armed."""
        if self.fail_on_append:
            self.fail_on_append -= 1
            raise RuntimeError("synthetic turn failure")
        stored = turn.model_copy(
            update={
                "turn_id": len(self.turns) + 1,
                "turn_index": len(self.turns),
            }
        )
        self.turns.append(stored)
        return stored


@pytest.fixture()
def knowledge_root(tmp_path: Path) -> Path:
    """A synthetic legacy knowledge tree: top-level + tenants."""
    root = tmp_path / "knowledge"
    (root / "tenants" / "tenant-a").mkdir(parents=True)
    (root / "tenants" / "tenant-unknown").mkdir(parents=True)
    (root / "2024-05-01.md").write_text(LEGACY_FILE_ONE, encoding="utf-8")
    (root / "2024-05-02.md").write_text(LEGACY_FILE_TWO, encoding="utf-8")
    (root / "tenants" / "tenant-a" / "2024-05-01.md").write_text(
        TENANT_FILE, encoding="utf-8"
    )
    (root / "tenants" / "tenant-unknown" / "2024-05-03.md").write_text(
        TENANT_FILE, encoding="utf-8"
    )
    return root


@pytest.fixture()
def engine(tmp_path: Path) -> Engine:
    """An explicit temporary SQLite engine (never the live DB)."""
    created = create_engine(f"sqlite:///{tmp_path / 'b14.sqlite'}")
    yield created
    created.dispose()


def _snapshot_files(root: Path) -> dict[str, bytes]:
    """Return every fixture file's bytes keyed by relative path."""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*.md"))
    }


def _assert_files_unchanged(root: Path, snapshot: dict[str, bytes]) -> None:
    """Assert every fixture file is byte-identical to a snapshot."""
    assert _snapshot_files(root) == snapshot


def _conversation_value() -> list[dict[str, object]]:
    """One legacy ``Conversation.value`` payload (user + bot)."""
    return [
        {"is_bot": False, "name": "User", "content": "Hello there"},
        {"is_bot": True, "name": "Bot", "content": "Hello back"},
    ]


def _known_conversation() -> LegacyConversation:
    """One legacy conversation with a known chatbot link."""
    return legacy_conversation(7, int(BOT_PRIMARY), _conversation_value())


def _unknown_conversations() -> tuple[LegacyConversation, ...]:
    """Legacy conversations with missing and unlisted owners."""
    return (
        legacy_conversation(8, None, _conversation_value()),
        legacy_conversation(9, 99, _conversation_value()),
    )


def _full_request(
    knowledge_root: Path,
    conversations: tuple[LegacyConversation, ...],
) -> MigrationRequest:
    """One request where every fixture source has an explicit owner."""
    return MigrationRequest(
        knowledge_root=knowledge_root,
        conversations=conversations,
        owner_map={
            "tenant-a": BOT_PRIMARY,
            "tenant-unknown": BOT_PRIMARY,
        },
        default_owner=BOT_PRIMARY,
        known_chatbots=frozenset({int(BOT_PRIMARY)}),
    )


def _partial_request(
    knowledge_root: Path,
) -> MigrationRequest:
    """One request leaving most sources without an explicit owner."""
    return MigrationRequest(
        knowledge_root=knowledge_root,
        conversations=(
            _known_conversation(),
            *_unknown_conversations(),
        ),
        owner_map={"tenant-a": BOT_PRIMARY},
        default_owner=None,
        known_chatbots=frozenset({int(BOT_PRIMARY)}),
    )
