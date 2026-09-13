"""Regression tests for release issue B02.

Proves ``SqlCompanionMemoryRepository`` (the first concrete
``CompanionMemoryRepository`` implementation, backed by Desktop's own
SQLAlchemy/SQLite database) satisfies B02's acceptance criteria:

- Fake-clock boundary cases create the expected sessions (the
  characterized inactivity-gap rotation rule, W01 §2).
- A repeated completion event is idempotent, and different chatbots
  never share turns even when they reuse the same call_chain_id.
- Fresh and historical SQLite fixtures migrate to the new
  ``companion_sessions``/``companion_turns`` tables without losing
  existing records.

Uses only temporary, explicit SQLite databases (never the owner's
active environment) and a fake clock -- no real model, network, or GUI
access.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.models.companion_turn import CompanionTurn
from airunner_services.database.session import reset_engine, session_scope
from airunner_services.database.setup_database import setup_database
from airunner_services.llm.companion.contracts import (
    CallChainId,
    ChatbotId,
)
from airunner_services.llm.companion.memory_repository import TurnRecord
from airunner_services.llm.companion.repository import (
    DEFAULT_SESSION_GAP,
    SqlCompanionMemoryRepository,
)

_PRIOR_HEAD_REVISION = "0f8b4e43d1c2"


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'release-b02.sqlite'}"
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


# --- Fake-clock session-rotation boundary cases ---


def test_first_call_starts_a_new_session(test_db, repo, fake_clock) -> None:
    chatbot_id = _make_chatbot()
    session = repo.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    assert session.chatbot_id == chatbot_id


def test_within_gap_reuses_the_same_session(test_db, repo, fake_clock) -> None:
    chatbot_id = _make_chatbot()
    first = repo.get_or_start_session(chatbot_id)

    fake_clock.now += DEFAULT_SESSION_GAP - timedelta(seconds=1)
    second = repo.get_or_start_session(chatbot_id)

    assert second.session_id == first.session_id


def test_exactly_at_gap_boundary_still_reuses_the_session(
    test_db, repo, fake_clock
) -> None:
    """The gap check is a strict '<', so a delta exactly equal to the
    threshold is still "within" it (release issue B02 fake-clock
    boundary acceptance criterion)."""
    chatbot_id = _make_chatbot()
    first = repo.get_or_start_session(chatbot_id)

    fake_clock.now += DEFAULT_SESSION_GAP - timedelta(microseconds=1)
    second = repo.get_or_start_session(chatbot_id)

    assert second.session_id == first.session_id


def test_past_gap_starts_a_new_session(test_db, repo, fake_clock) -> None:
    chatbot_id = _make_chatbot()
    first = repo.get_or_start_session(chatbot_id)

    fake_clock.now += DEFAULT_SESSION_GAP + timedelta(seconds=1)
    second = repo.get_or_start_session(chatbot_id)

    assert second.session_id != first.session_id


def test_appending_a_turn_extends_the_activity_window(
    test_db, repo, fake_clock
) -> None:
    """Activity (a turn) resets the inactivity clock, not merely asking
    for the session: appending a turn just under the boundary, then
    checking again just under a fresh boundary from that turn, must
    still resolve to the same session."""
    chatbot_id = _make_chatbot()
    session = repo.get_or_start_session(chatbot_id)

    fake_clock.now += DEFAULT_SESSION_GAP - timedelta(minutes=1)
    repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session.session_id,
            role="user",
            content="hello",
            call_chain_id=CallChainId("cc-1"),
        )
    )

    fake_clock.now += DEFAULT_SESSION_GAP - timedelta(minutes=1)
    still_same = repo.get_or_start_session(chatbot_id)
    assert still_same.session_id == session.session_id


# --- Idempotency and chatbot isolation ---


def test_repeated_completion_event_is_idempotent(test_db, repo) -> None:
    chatbot_id = _make_chatbot()
    session = repo.get_or_start_session(chatbot_id)
    call_chain_id = CallChainId("cc-repeat")

    first = repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session.session_id,
            role="assistant",
            content="hi there",
            call_chain_id=call_chain_id,
        )
    )
    second = repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session.session_id,
            role="assistant",
            content="hi there",
            call_chain_id=call_chain_id,
        )
    )

    assert first.turn_id == second.turn_id
    with session_scope() as db:
        count = (
            db.query(CompanionTurn)
            .filter(CompanionTurn.chatbot_id == int(chatbot_id))
            .count()
        )
    assert count == 1


def test_user_and_assistant_turns_share_call_chain_id_without_colliding(
    test_db, repo
) -> None:
    """One request produces two turns (user, assistant) sharing one
    call_chain_id -- role must be part of the idempotency key, not
    call_chain_id alone."""
    chatbot_id = _make_chatbot()
    session = repo.get_or_start_session(chatbot_id)
    call_chain_id = CallChainId("cc-shared")

    user_turn = repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session.session_id,
            role="user",
            content="what's the weather?",
            call_chain_id=call_chain_id,
        )
    )
    assistant_turn = repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session.session_id,
            role="assistant",
            content="sunny",
            call_chain_id=call_chain_id,
        )
    )

    assert user_turn.turn_id != assistant_turn.turn_id
    assert user_turn.turn_index == 0
    assert assistant_turn.turn_index == 1


def test_different_chatbots_never_share_turns(test_db, repo) -> None:
    """Two different chatbots reusing the identical call_chain_id/role
    must not collide -- chatbot_id is part of the idempotency key."""
    chatbot_a = _make_chatbot()
    chatbot_b = _make_chatbot()
    session_a = repo.get_or_start_session(chatbot_a)
    session_b = repo.get_or_start_session(chatbot_b)
    call_chain_id = CallChainId("cc-colliding")

    turn_a = repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_a,
            session_id=session_a.session_id,
            role="user",
            content="from bot A",
            call_chain_id=call_chain_id,
        )
    )
    turn_b = repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_b,
            session_id=session_b.session_id,
            role="user",
            content="from bot B",
            call_chain_id=call_chain_id,
        )
    )

    assert turn_a.turn_id != turn_b.turn_id
    with session_scope() as db:
        count = db.query(CompanionTurn).count()
    assert count == 2


def test_get_recent_turns_returns_oldest_first_within_limit(
    test_db, repo
) -> None:
    chatbot_id = _make_chatbot()
    session = repo.get_or_start_session(chatbot_id)
    for index in range(5):
        repo.append_turn(
            TurnRecord(
                chatbot_id=chatbot_id,
                session_id=session.session_id,
                role="user",
                content=f"message {index}",
                call_chain_id=CallChainId(f"cc-{index}"),
            )
        )

    recent = repo.get_recent_turns(chatbot_id, session.session_id, limit=3)
    assert [turn.content for turn in recent] == [
        "message 2",
        "message 3",
        "message 4",
    ]


def test_update_session_summary_persists_fields(test_db, repo) -> None:
    chatbot_id = _make_chatbot()
    session = repo.get_or_start_session(chatbot_id)
    updated = session.model_copy(
        update={
            "episodic_summary": "a quiet chat about the weather",
            "rolling_summary": "ongoing weather talk",
            "emotional_weight": 0.5,
            "key_topics": ["weather", "small talk"],
            "summary_ready": True,
        }
    )

    repo.update_session_summary(updated)

    with session_scope() as db:
        row = (
            db.query(CompanionSession)
            .filter(CompanionSession.id == int(session.session_id))
            .one()
        )
        assert row.episodic_summary == "a quiet chat about the weather"
        assert row.summary_ready is True
        assert row.key_topics == ["weather", "small talk"]


def test_get_facts_returns_empty_and_upsert_fact_is_not_implemented(
    test_db, repo
) -> None:
    """Fact storage is B03's scope; this confirms the honest placeholder
    behavior documented in repository.py."""
    chatbot_id = _make_chatbot()
    assert repo.get_facts(chatbot_id, limit=10) == []
    with pytest.raises(NotImplementedError):
        repo.upsert_fact(object())  # type: ignore[arg-type]


# --- Migration: fresh and historical SQLite fixtures ---


def test_fresh_sqlite_database_gets_companion_tables(test_db) -> None:
    from sqlalchemy import inspect

    from airunner_services.database.db.engine import create_configured_engine

    engine = create_configured_engine(test_db)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert "companion_sessions" in tables
    assert "companion_turns" in tables


def test_historical_database_migrates_without_losing_existing_records(
    tmp_path, monkeypatch
) -> None:
    """A database representing an existing user's current schema (every
    table except the two new B02 ones) must, after upgrading, gain
    ``companion_sessions``/``companion_turns`` and keep every
    pre-existing row untouched (release issue B02 acceptance
    criterion).

    Built by creating every table already on ``Base.metadata`` *except*
    the two new ones and stamping ``alembic_version`` at the prior
    head(s) -- not by running ``alembic upgrade`` from an empty
    database. This repo's very first migration
    (``181e31f78151_initial_migration.py``) unconditionally calls
    ``Base.metadata.create_all()``; since ``Base`` is one shared object
    for this whole process and the companion models are already
    imported, replaying history from scratch would create the new
    tables immediately regardless of target revision, defeating the
    point of this fixture. Stamping (no scripts executed) avoids that
    entirely and is what a real pre-existing database's state on disk
    actually looks like.

    This repo's migration history also has two independent unmerged
    heads (``0f8b4e43d1c2`` and ``a7c93f2e1b4d``, pre-existing and out
    of scope for this ticket) -- both are stamped to accurately model
    "already at every current head" before the new one is introduced.
    """
    from sqlalchemy import inspect
    from sqlalchemy.orm import sessionmaker

    from airunner_services.database.base import Base
    from airunner_services.database.db.engine import create_configured_engine
    import airunner_services.database.models  # noqa: F401 -- populates Base.metadata

    other_prior_head = "a7c93f2e1b4d"

    db_path = tmp_path / "historical.sqlite"
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
        pre_b02_tables = [
            table
            for name, table in Base.metadata.tables.items()
            if name not in ("companion_sessions", "companion_turns")
        ]
        Base.metadata.create_all(bind=engine, tables=pre_b02_tables)
        command.stamp(alembic_cfg, [_PRIOR_HEAD_REVISION, other_prior_head])

        pre_tables = set(inspect(engine).get_table_names())
        assert "companion_sessions" not in pre_tables
        assert "companion_turns" not in pre_tables

        Session = sessionmaker(bind=engine)
        with Session() as db:
            existing = Chatbot(name="pre-existing-bot")
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
        assert "companion_sessions" in post_tables
        assert "companion_turns" in post_tables

        Session = sessionmaker(bind=engine)
        with Session() as db:
            row = db.query(Chatbot).filter(Chatbot.id == existing_id).one()
            assert row.name == "pre-existing-bot"
    finally:
        engine.dispose()
        reset_engine()
