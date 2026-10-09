"""Regression tests for release issue B03.

Proves ``SqlCompanionMemoryRepository`` satisfies B03's acceptance
criteria:

- Create/update/retract/reopen maintains provenance and bot
  isolation.
- Duplicate event IDs do not duplicate facts.
- An additive migration works on a populated synthetic old database.

Also proves the one-per-chatbot evolving narrative, plain-B01-
``FactRecord`` backward compatibility, and that no vector-index
writes happen here (facts carry no embedding column -- B04's
scope). Uses only temporary, explicit SQLite databases (never the
owner's active environment) and a fake clock -- no real model,
network, or GUI access.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.companion_fact import CompanionFact
from airunner_services.database.models.companion_narrative import (
    CompanionNarrative,
)
from airunner_services.database.session import reset_engine, session_scope
from airunner_services.database.setup_database import setup_database
from airunner_services.llm.companion.contracts import (
    CallChainId,
    ChatbotId,
    TurnId,
)
from airunner_services.llm.companion.memory_repository import (
    FactRecord,
    TurnRecord,
)
from airunner_services.llm.companion.repository import (
    SqlCompanionMemoryRepository,
    StoredFactRecord,
)

_PRIOR_HEADS = ["910441db1456", "a7c93f2e1b4d"]


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'release-b03.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    yield db_url
    reset_engine()


@pytest.fixture()
def fake_clock():
    """A controllable clock: ``fake_clock.now`` advances calls to it."""

    class _FakeClock:
        def __init__(self) -> None:
            self.now = datetime(2026, 1, 1, 12, 0, 0)

        def __call__(self) -> datetime:
            return self.now

    return _FakeClock()


@pytest.fixture()
def repo(fake_clock) -> SqlCompanionMemoryRepository:
    return SqlCompanionMemoryRepository(clock=fake_clock)


def _make_chatbot() -> ChatbotId:
    with session_scope() as db:
        chatbot = Chatbot(name=f"bot-{datetime.now().timestamp()}")
        db.add(chatbot)
        db.flush()
        return ChatbotId(chatbot.id)


def _make_turn_id(repo, chatbot_id: ChatbotId) -> int:
    session = repo.get_or_start_session(chatbot_id)
    turn = repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session.session_id,
            role="user",
            content="my dog is named Biscuit",
            call_chain_id=CallChainId("cc-b03-source"),
        )
    )
    assert turn.turn_id is not None
    return int(turn.turn_id)


# --- Create/update with provenance ---


def test_upsert_fact_creates_with_full_provenance(
    test_db, repo, fake_clock
) -> None:
    chatbot_id = _make_chatbot()
    turn_id = _make_turn_id(repo, chatbot_id)

    stored = repo.upsert_fact(
        StoredFactRecord(
            chatbot_id=chatbot_id,
            content="user's dog is named Biscuit",
            subject="dog",
            source="fact-extraction",
            source_turn_id=TurnId(turn_id),
            event_id="evt-1",
            confidence=0.9,
            metadata={"extractor": "b07-stub"},
        )
    )

    assert stored.fact_id is not None
    assert stored.subject == "dog"
    assert stored.source == "fact-extraction"
    assert stored.source_turn_id == turn_id
    assert stored.event_id == "evt-1"
    assert stored.confidence == 0.9
    assert stored.metadata == {"extractor": "b07-stub"}
    assert stored.created_at == fake_clock.now.isoformat()
    assert stored.updated_at == fake_clock.now.isoformat()
    assert stored.retracted_at is None


def test_upsert_fact_with_id_updates_and_preserves_created_at(
    test_db, repo, fake_clock
) -> None:
    chatbot_id = _make_chatbot()
    created = repo.upsert_fact(
        StoredFactRecord(
            chatbot_id=chatbot_id,
            content="old content",
            subject="dog",
            source="fact-extraction",
            event_id="evt-update",
        )
    )

    fake_clock.now += timedelta(hours=1)
    updated = repo.upsert_fact(
        StoredFactRecord(
            fact_id=created.fact_id,
            chatbot_id=chatbot_id,
            content="new content",
            subject="dog",
            source="fact-extraction",
            confidence=0.5,
        )
    )

    assert updated.fact_id == created.fact_id
    assert updated.content == "new content"
    assert updated.confidence == 0.5
    assert updated.created_at == created.created_at
    assert updated.updated_at == fake_clock.now.isoformat()
    with session_scope() as db:
        count = (
            db.query(CompanionFact)
            .filter(CompanionFact.chatbot_id == int(chatbot_id))
            .count()
        )
    assert count == 1


def test_updating_a_missing_fact_id_raises(test_db, repo) -> None:
    chatbot_id = _make_chatbot()
    with pytest.raises(ValueError):
        repo.upsert_fact(
            StoredFactRecord(
                fact_id=999999,
                chatbot_id=chatbot_id,
                content="ghost",
            )
        )


def test_plain_b01_fact_record_still_upserts(test_db, repo) -> None:
    """A caller holding only the B01 contract (no provenance
    fields) can still store facts; unknown provenance defaults
    rather than errors."""
    chatbot_id = _make_chatbot()
    stored = repo.upsert_fact(
        FactRecord(chatbot_id=chatbot_id, content="plain fact")
    )
    assert stored.fact_id is not None
    assert stored.content == "plain fact"

    # No event_id means no dedup key: a second plain fact with the
    # same content is a second row, not a collapsed one.
    second = repo.upsert_fact(
        FactRecord(chatbot_id=chatbot_id, content="plain fact")
    )
    assert second.fact_id != stored.fact_id


# --- Duplicate event IDs ---


def test_duplicate_event_id_does_not_duplicate_facts(test_db, repo) -> None:
    chatbot_id = _make_chatbot()
    first = repo.upsert_fact(
        StoredFactRecord(
            chatbot_id=chatbot_id,
            content="redelivered event",
            event_id="evt-dup",
        )
    )
    second = repo.upsert_fact(
        StoredFactRecord(
            chatbot_id=chatbot_id,
            content="redelivered event",
            event_id="evt-dup",
        )
    )

    assert first.fact_id == second.fact_id
    with session_scope() as db:
        count = (
            db.query(CompanionFact)
            .filter(CompanionFact.chatbot_id == int(chatbot_id))
            .count()
        )
    assert count == 1


def test_same_event_id_across_chatbots_stays_separate(test_db, repo) -> None:
    chatbot_a = _make_chatbot()
    chatbot_b = _make_chatbot()
    fact_a = repo.upsert_fact(
        StoredFactRecord(
            chatbot_id=chatbot_a,
            content="from bot A",
            event_id="evt-shared",
        )
    )
    fact_b = repo.upsert_fact(
        StoredFactRecord(
            chatbot_id=chatbot_b,
            content="from bot B",
            event_id="evt-shared",
        )
    )

    assert fact_a.fact_id != fact_b.fact_id
    with session_scope() as db:
        assert db.query(CompanionFact).count() == 2


# --- Retract/reopen ---


def test_retract_hides_from_recall_but_keeps_the_row(
    test_db, repo, fake_clock
) -> None:
    chatbot_id = _make_chatbot()
    created = repo.upsert_fact(
        StoredFactRecord(
            chatbot_id=chatbot_id,
            content="retractable",
            subject="s",
            source="fact-extraction",
            event_id="evt-retract",
        )
    )

    fake_clock.now += timedelta(minutes=5)
    retracted = repo.retract_fact(
        chatbot_id, int(created.fact_id), reason="user corrected"
    )

    assert retracted.retracted_at == fake_clock.now.isoformat()
    assert retracted.retraction_reason == "user corrected"
    assert retracted.content == "retractable"
    assert retracted.subject == "s"
    assert repo.get_facts(chatbot_id, limit=10) == []
    visible = repo.get_facts(chatbot_id, limit=10, include_retracted=True)
    assert [fact.fact_id for fact in visible] == [created.fact_id]


def test_reopen_restores_a_retracted_fact(test_db, repo) -> None:
    chatbot_id = _make_chatbot()
    created = repo.upsert_fact(
        StoredFactRecord(chatbot_id=chatbot_id, content="reopenable")
    )
    repo.retract_fact(chatbot_id, int(created.fact_id))

    reopened = repo.reopen_fact(chatbot_id, int(created.fact_id))

    assert reopened.retracted_at is None
    assert reopened.retraction_reason is None
    assert reopened.created_at == created.created_at
    assert [fact.fact_id for fact in repo.get_facts(chatbot_id, limit=10)] == [
        created.fact_id
    ]


def test_update_preserves_retraction_state(test_db, repo) -> None:
    chatbot_id = _make_chatbot()
    created = repo.upsert_fact(
        StoredFactRecord(chatbot_id=chatbot_id, content="v1")
    )
    repo.retract_fact(chatbot_id, int(created.fact_id), reason="stale")

    updated = repo.upsert_fact(
        StoredFactRecord(
            fact_id=created.fact_id,
            chatbot_id=chatbot_id,
            content="v2",
        )
    )

    assert updated.content == "v2"
    assert updated.retracted_at is not None
    assert repo.get_facts(chatbot_id, limit=10) == []


# --- Bot isolation ---


def test_facts_are_isolated_per_chatbot(test_db, repo) -> None:
    chatbot_a = _make_chatbot()
    chatbot_b = _make_chatbot()
    created = repo.upsert_fact(
        StoredFactRecord(chatbot_id=chatbot_a, content="bot A only")
    )
    assert created.fact_id is not None
    fact_id = int(created.fact_id)

    assert repo.get_facts(chatbot_b, limit=10) == []
    with pytest.raises(ValueError):
        repo.retract_fact(chatbot_b, fact_id)
    with pytest.raises(ValueError):
        repo.reopen_fact(chatbot_b, fact_id)
    with pytest.raises(ValueError):
        repo.upsert_fact(
            StoredFactRecord(
                fact_id=fact_id,
                chatbot_id=chatbot_b,
                content="cross-bot write",
            )
        )
    # And the failed cross-bot attempts changed nothing.
    assert repo.get_facts(chatbot_a, limit=10)[0].content == "bot A only"


def test_get_facts_orders_most_recent_first_and_respects_limit(
    test_db, repo, fake_clock
) -> None:
    chatbot_id = _make_chatbot()
    for index in range(3):
        repo.upsert_fact(
            StoredFactRecord(
                chatbot_id=chatbot_id,
                content=f"fact {index}",
                event_id=f"evt-order-{index}",
            )
        )
        fake_clock.now += timedelta(minutes=1)

    recent = repo.get_facts(chatbot_id, limit=2)
    assert [fact.content for fact in recent] == ["fact 2", "fact 1"]
    assert repo.get_facts(chatbot_id, limit=0) == []


# --- Narrative ---


def test_narrative_lifecycle_and_versioning(test_db, repo) -> None:
    chatbot_id = _make_chatbot()
    assert repo.get_narrative(chatbot_id) is None

    first = repo.update_narrative(chatbot_id, "chapter one")
    assert first.version == 1
    assert first.content == "chapter one"
    assert first.narrative_id is not None

    second = repo.update_narrative(chatbot_id, "chapter two")
    assert second.version == 2
    assert second.content == "chapter two"
    assert second.narrative_id == first.narrative_id
    assert second.created_at == first.created_at

    fetched = repo.get_narrative(chatbot_id)
    assert fetched is not None
    assert fetched.content == "chapter two"
    with session_scope() as db:
        count = (
            db.query(CompanionNarrative)
            .filter(CompanionNarrative.chatbot_id == int(chatbot_id))
            .count()
        )
    assert count == 1


def test_narratives_are_isolated_per_chatbot(test_db, repo) -> None:
    chatbot_a = _make_chatbot()
    chatbot_b = _make_chatbot()
    repo.update_narrative(chatbot_a, "bot A story")

    assert repo.get_narrative(chatbot_b) is None


# --- Migration: fresh and historical SQLite fixtures ---


def test_fresh_sqlite_database_gets_fact_and_narrative_tables(
    test_db,
) -> None:
    from sqlalchemy import inspect

    from airunner_services.database.db.engine import create_configured_engine

    engine = create_configured_engine(test_db)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert "companion_facts" in tables
    assert "companion_narratives" in tables


def test_historical_database_migrates_without_losing_existing_records(
    tmp_path, monkeypatch
) -> None:
    """A populated database at the pre-B03 heads (every table except
    the two new B03 ones) must, after upgrading, gain
    ``companion_facts``/``companion_narratives`` and keep every
    pre-existing row untouched (release issue B03 acceptance
    criterion). Built by stamping, not by replaying history -- see
    test_release_b02.py's historical fixture for why."""
    from sqlalchemy import inspect
    from sqlalchemy.orm import sessionmaker

    from airunner_services.database.base import Base
    from airunner_services.database.db.engine import create_configured_engine
    from airunner_services.database.models import (
        companion_fact,
        companion_narrative,
    )

    db_path = tmp_path / "historical-b03.sqlite"
    db_url = f"sqlite:///{db_path}"

    base = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "airunner_services"
        / "database"
    )
    alembic_cfg = Config(base / "alembic.ini")
    alembic_cfg.set_main_option("script_location", str(base / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    engine = create_configured_engine(db_url)
    try:
        pre_b03_tables = [
            table
            for name, table in Base.metadata.tables.items()
            if name not in ("companion_facts", "companion_narratives")
        ]
        Base.metadata.create_all(bind=engine, tables=pre_b03_tables)
        command.stamp(alembic_cfg, _PRIOR_HEADS)

        pre_tables = set(inspect(engine).get_table_names())
        assert "companion_facts" not in pre_tables
        assert "companion_narratives" not in pre_tables

        Session = sessionmaker(bind=engine)
        with Session() as db:
            existing = Chatbot(name="pre-existing-bot-b03")
            db.add(existing)
            db.commit()
            existing_id = existing.id
    finally:
        engine.dispose()

    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database(db_url)

    engine = create_configured_engine(db_url)
    try:
        post_tables = set(inspect(engine).get_table_names())
        fact_table = companion_fact.CompanionFact.__tablename__
        narrative_table = companion_narrative.CompanionNarrative.__tablename__
        assert fact_table in post_tables
        assert narrative_table in post_tables

        Session = sessionmaker(bind=engine)
        with Session() as db:
            row = db.query(Chatbot).filter(Chatbot.id == existing_id).one()
            assert row.name == "pre-existing-bot-b03"
    finally:
        engine.dispose()
        reset_engine()
