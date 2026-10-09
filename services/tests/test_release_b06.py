"""Regression tests for release issue B06.

Proves ``DurableCompanionScheduler`` (the durable ``CompanionScheduler``
implementation, backed by Desktop's own SQLAlchemy/SQLite database)
satisfies B06's acceptance criteria:

- Duplicate enqueue and process restart do not duplicate effects.
- Queue limits and cancellation are deterministic.
- A crashed leased job can recover with capped retries.

Also proves the mechanism behind those criteria: leases with fenced
completion, bounded concurrency, retry backoff, injected clock/
executor/arbitration (GPU work only through the injected entry point,
never a model load here), and additive migration of the new
``companion_jobs`` table.

Uses only temporary, explicit SQLite databases (never the owner's
active environment) and a fake clock -- no real model, network, or
GUI access.
"""

from __future__ import annotations

import importlib
import itertools
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest
from alembic import command
from alembic.config import Config

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.companion_job import CompanionJob
from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.session import reset_engine, session_scope
from airunner_services.database.setup_database import setup_database
from airunner_services.llm.companion.contracts import (
    ChatbotId,
    SessionId,
)
from airunner_services.llm.companion.jobs import (
    JOB_CANCELLED,
    JOB_FAILED,
    JOB_LEASED,
    JOB_QUEUED,
    JOB_SUCCEEDED,
    DurableCompanionScheduler,
    JobContext,
)
from airunner_services.llm.companion.scheduler import (
    CompanionJobRequest,
    CompanionJobType,
    CompanionScheduler,
)

# The two heads before this issue's own new revision (which chains off
# 910441db1456): the historical fixture stamps these to model "a real
# pre-existing database already at every head". Stamp heads only --
# adding any of their ancestors as a separate version row makes
# alembic's upgrade resolution fail with an overlap error.
_PRIOR_HEADS = [
    "910441db1456",
    "a7c93f2e1b4d",
]

_chatbot_counter = itertools.count()


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'release-b06.sqlite'}"
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
def scheduler(fake_clock) -> DurableCompanionScheduler:
    produced = DurableCompanionScheduler(clock=fake_clock)
    assert isinstance(produced, CompanionScheduler)
    return produced


def _make_chatbot() -> ChatbotId:
    with session_scope() as db:
        index = next(_chatbot_counter)
        chatbot = Chatbot(name=f"b06-bot-{index}")
        db.add(chatbot)
        db.flush()
        return ChatbotId(chatbot.id)


def _make_session(chatbot_id: ChatbotId, now: datetime) -> SessionId:
    with session_scope() as db:
        row = CompanionSession(
            chatbot_id=int(chatbot_id),
            started_at=now,
            last_message_at=now,
            summary_ready=False,
        )
        db.add(row)
        db.flush()
        return SessionId(row.id)


def _request(
    chatbot_id: ChatbotId,
    key: str,
    job_type: CompanionJobType = CompanionJobType.MOOD_UPDATE,
    session_id: Optional[SessionId] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> CompanionJobRequest:
    return CompanionJobRequest(
        job_type=job_type,
        chatbot_id=chatbot_id,
        session_id=session_id,
        idempotency_key=key,
        payload=payload or {},
    )


def _set_lease(
    job_id: str, owner: str, expires_at: datetime, attempts: int
) -> None:
    """Force one row into the exact state a worker leaves behind.

    A live lease (``expires_at`` in the future) models another worker
    currently holding the job; an expired one models a worker that
    crashed -- or an old process that no longer exists -- without
    completing it.
    """
    with session_scope() as db:
        row = (
            db.query(CompanionJob).filter(CompanionJob.id == int(job_id)).one()
        )
        row.status = JOB_LEASED
        row.lease_owner = owner
        row.lease_expires_at = expires_at
        row.attempts = attempts


def _row(job_id: str) -> CompanionJob:
    with session_scope() as db:
        row = (
            db.query(CompanionJob).filter(CompanionJob.id == int(job_id)).one()
        )
        db.expunge(row)
        return row


def _count(chatbot_id: ChatbotId) -> int:
    with session_scope() as db:
        return (
            db.query(CompanionJob)
            .filter(CompanionJob.chatbot_id == int(chatbot_id))
            .count()
        )


# --- Persistence and idempotent enqueue ---


def test_schedule_persists_a_queued_job(test_db, scheduler, fake_clock):
    chatbot_id = _make_chatbot()
    session_id = _make_session(chatbot_id, fake_clock.now)

    handle = scheduler.schedule(
        _request(
            chatbot_id,
            "key-1",
            session_id=session_id,
            payload={"turn_id": 7},
        )
    )

    assert handle.accepted is True
    assert handle.job_id != ""
    row = _row(handle.job_id)
    assert row.status == JOB_QUEUED
    assert row.job_type == CompanionJobType.MOOD_UPDATE.value
    assert row.chatbot_id == int(chatbot_id)
    assert row.session_id == int(session_id)
    assert row.idempotency_key == "key-1"
    assert row.payload == {"turn_id": 7}
    assert row.attempts == 0
    assert row.run_after == fake_clock.now


def test_duplicate_enqueue_is_a_noop_with_a_single_effect(test_db, scheduler):
    """The same idempotency key twice stores one row and runs once."""
    chatbot_id = _make_chatbot()
    effects: List[str] = []
    scheduler.register_handler(
        CompanionJobType.MOOD_UPDATE,
        lambda context: effects.append(context.job_id),
    )

    first = scheduler.schedule(_request(chatbot_id, "key-dup"))
    second = scheduler.schedule(_request(chatbot_id, "key-dup"))

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "duplicate"
    assert second.job_id == first.job_id
    assert _count(chatbot_id) == 1

    outcomes = scheduler.run_due("worker-1")

    assert len(outcomes) == 1
    assert outcomes[0].status == JOB_SUCCEEDED
    assert effects == [first.job_id]
    assert scheduler.run_due("worker-1") == []


def test_different_keys_and_types_do_not_collide(test_db, scheduler):
    chatbot_id = _make_chatbot()

    first = scheduler.schedule(_request(chatbot_id, "key-a"))
    second = scheduler.schedule(_request(chatbot_id, "key-b"))
    third = scheduler.schedule(
        _request(
            chatbot_id,
            "key-a",
            job_type=CompanionJobType.CURIOSITY,
        )
    )

    assert first.accepted and second.accepted and third.accepted
    assert len({first.job_id, second.job_id, third.job_id}) == 3


def test_unknown_chatbot_or_session_is_rejected(test_db, scheduler):
    chatbot_id = _make_chatbot()

    with pytest.raises(ValueError):
        scheduler.schedule(_request(ChatbotId(999999), "key-x"))
    with pytest.raises(ValueError):
        scheduler.schedule(
            _request(chatbot_id, "key-y", session_id=SessionId(999999))
        )


# --- Restart recovery ---


def test_restart_recovers_crashed_lease_without_duplicate_effects(
    test_db, fake_clock
):
    """A lease held by a dead process runs exactly once afterwards."""
    old_process = DurableCompanionScheduler(clock=fake_clock)
    chatbot_id = _make_chatbot()
    handle = old_process.schedule(_request(chatbot_id, "key-crash"))
    # The old process claimed the job, then died: attempts were
    # incremented at claim time, but no completion was ever written.
    _set_lease(
        handle.job_id,
        "dead-worker",
        fake_clock.now + timedelta(minutes=5),
        attempts=1,
    )
    del old_process

    effects: List[str] = []
    restarted = DurableCompanionScheduler(clock=fake_clock)
    restarted.register_handler(
        CompanionJobType.MOOD_UPDATE,
        lambda context: effects.append(context.job_id),
    )

    # Before the lease expires the job still belongs to its (dead but
    # unexpired) owner: nothing to run.
    assert restarted.run_due("new-worker") == []
    assert effects == []

    fake_clock.now += timedelta(minutes=6)
    assert restarted.recover_expired_leases() == 1

    outcomes = restarted.run_due("new-worker")

    assert len(outcomes) == 1
    assert outcomes[0].status == JOB_SUCCEEDED
    assert outcomes[0].attempts == 2
    assert effects == [handle.job_id]
    # And a re-enqueue after the restart is still a duplicate.
    repeat = restarted.schedule(_request(chatbot_id, "key-crash"))
    assert repeat.accepted is False
    assert repeat.reason == "duplicate"


# --- Deterministic queue limits and cancellation ---


def test_queue_limit_is_deterministic(test_db, fake_clock):
    capped = DurableCompanionScheduler(
        clock=fake_clock, max_pending_per_chatbot=2
    )
    chatbot_id = _make_chatbot()

    first = capped.schedule(_request(chatbot_id, "key-1"))
    second = capped.schedule(_request(chatbot_id, "key-2"))
    third = capped.schedule(_request(chatbot_id, "key-3"))

    assert first.accepted is True
    assert second.accepted is True
    assert third.accepted is False
    assert third.reason == "queue_full"
    assert third.job_id == ""
    assert _count(chatbot_id) == 2

    # Cancelling one frees exactly one slot; the bound is per-chatbot
    # so an unrelated chatbot is unaffected either way.
    assert capped.cancel(first.job_id) is True
    other_bot = _make_chatbot()
    other = capped.schedule(_request(other_bot, "key-1"))
    assert other.accepted is True
    fourth = capped.schedule(_request(chatbot_id, "key-4"))
    assert fourth.accepted is True
    fifth = capped.schedule(_request(chatbot_id, "key-5"))
    assert fifth.accepted is False
    assert fifth.reason == "queue_full"


def test_cancel_is_deterministic(test_db, scheduler):
    chatbot_id = _make_chatbot()
    calls: List[str] = []
    scheduler.register_handler(
        CompanionJobType.MOOD_UPDATE,
        lambda context: calls.append(context.job_id),
    )
    handle = scheduler.schedule(_request(chatbot_id, "key-cancel"))

    assert scheduler.cancel(handle.job_id) is True
    assert _row(handle.job_id).status == JOB_CANCELLED
    # Terminal, unknown, and malformed ids are False, never an error.
    assert scheduler.cancel(handle.job_id) is False
    assert scheduler.cancel("999999") is False
    assert scheduler.cancel("not-an-id") is False
    assert scheduler.cancel("") is False

    # A cancelled job never runs.
    assert scheduler.run_due("worker-1") == []
    assert calls == []


def test_cancel_does_not_steal_a_live_lease(test_db, scheduler, fake_clock):
    chatbot_id = _make_chatbot()
    handle = scheduler.schedule(_request(chatbot_id, "key-leased"))
    _set_lease(
        handle.job_id,
        "other-worker",
        fake_clock.now + timedelta(minutes=5),
        attempts=1,
    )

    assert scheduler.cancel(handle.job_id) is False
    assert _row(handle.job_id).status == JOB_LEASED


# --- Leases, retries, and bounded concurrency ---


def test_failing_job_retries_with_backoff_then_fails_capped(
    test_db, fake_clock
):
    attempts_seen: List[int] = []

    def _always_fails(context: JobContext) -> None:
        attempts_seen.append(context.attempt)
        raise RuntimeError("boom")

    scheduler = DurableCompanionScheduler(
        clock=fake_clock,
        max_attempts=3,
        retry_backoff=timedelta(seconds=30),
    )
    scheduler.register_handler(CompanionJobType.CURIOSITY, _always_fails)
    chatbot_id = _make_chatbot()
    handle = scheduler.schedule(
        _request(chatbot_id, "key-retry", job_type=CompanionJobType.CURIOSITY)
    )

    first = scheduler.run_due("worker-1")
    assert len(first) == 1
    assert first[0].status == JOB_QUEUED
    assert first[0].attempts == 1
    assert first[0].error == "boom"
    assert _row(handle.job_id).run_after == (
        fake_clock.now + timedelta(seconds=30)
    )

    # Backoff has not elapsed: the pump finds nothing due.
    assert scheduler.run_due("worker-1") == []
    assert attempts_seen == [1]

    fake_clock.now += timedelta(seconds=30)
    second = scheduler.run_due("worker-1")
    assert len(second) == 1
    assert second[0].status == JOB_QUEUED
    assert second[0].attempts == 2

    fake_clock.now += timedelta(seconds=60)
    third = scheduler.run_due("worker-1")
    assert len(third) == 1
    assert third[0].status == JOB_FAILED
    assert third[0].attempts == 3
    assert attempts_seen == [1, 2, 3]

    # Capped: no further run ever picks it up again.
    fake_clock.now += timedelta(days=1)
    assert scheduler.run_due("worker-1") == []
    assert attempts_seen == [1, 2, 3]
    assert _row(handle.job_id).status == JOB_FAILED


def test_crashed_lease_at_cap_marks_failed_without_rerun(test_db, fake_clock):
    calls: List[str] = []
    scheduler = DurableCompanionScheduler(clock=fake_clock, max_attempts=2)
    scheduler.register_handler(
        CompanionJobType.MOOD_UPDATE,
        lambda context: calls.append(context.job_id),
    )
    chatbot_id = _make_chatbot()
    handle = scheduler.schedule(_request(chatbot_id, "key-cap"))
    _set_lease(
        handle.job_id,
        "dead-worker",
        fake_clock.now - timedelta(seconds=1),
        attempts=2,
    )

    assert scheduler.recover_expired_leases() == 1
    assert _row(handle.job_id).status == JOB_FAILED
    assert scheduler.run_due("worker-1") == []
    assert calls == []


def test_live_leases_count_against_max_concurrent(test_db, fake_clock):
    ran: List[str] = []
    scheduler = DurableCompanionScheduler(clock=fake_clock, max_concurrent=2)
    scheduler.register_handler(
        CompanionJobType.MOOD_UPDATE,
        lambda context: ran.append(context.job_id),
    )
    chatbot_id = _make_chatbot()
    first = scheduler.schedule(_request(chatbot_id, "key-first"))
    second = scheduler.schedule(_request(chatbot_id, "key-second"))
    third = scheduler.schedule(_request(chatbot_id, "key-third"))
    # Another live worker holds one of the two concurrency slots, so
    # only one of the two queued jobs can be claimed.
    _set_lease(
        first.job_id,
        "other-worker",
        fake_clock.now + timedelta(minutes=5),
        attempts=1,
    )

    outcomes = scheduler.run_due("worker-1", limit=5)

    assert [outcome.job_id for outcome in outcomes] == [second.job_id]
    assert ran == [second.job_id]

    # Once that lease expires it is recovered, and the remaining
    # jobs drain oldest-due first (the recovered job's run_after is
    # the recovery instant, so the longer-queued job goes first).
    fake_clock.now += timedelta(minutes=6)
    rest = scheduler.run_due("worker-1", limit=5)
    assert [outcome.job_id for outcome in rest] == [
        third.job_id,
        first.job_id,
    ]
    assert all(outcome.status == JOB_SUCCEEDED for outcome in rest)


def test_claim_without_a_registered_handler_fails_without_retry(
    test_db, scheduler
):
    chatbot_id = _make_chatbot()
    handle = scheduler.schedule(
        _request(
            chatbot_id,
            "key-no-handler",
            job_type=CompanionJobType.FACT_EXTRACTION,
        )
    )

    outcomes = scheduler.run_due("worker-1")

    assert len(outcomes) == 1
    assert outcomes[0].status == JOB_FAILED
    assert "no handler" in (outcomes[0].error or "")
    assert _row(handle.job_id).status == JOB_FAILED


# --- Injected boundaries: executor, arbitration, no model loads ---


def test_executor_and_arbitration_are_injected_not_imported(
    test_db, fake_clock
):
    executed: List[str] = []
    arbitrated: List[Any] = []

    def _recording_executor(thunk: Callable[[], None]) -> None:
        executed.append("thunk")
        thunk()

    def _fake_arbitrate(route: str, payload: Dict[str, Any]) -> str:
        arbitrated.append((route, payload))
        return "arbitrated-result"

    scheduler = DurableCompanionScheduler(
        clock=fake_clock,
        executor=_recording_executor,
        arbitrate=_fake_arbitrate,
    )

    seen: List[JobContext] = []

    def _handler(context: JobContext) -> None:
        seen.append(context)
        assert context.arbitrate is not None
        context.arbitrate("llm", {"prompt": "hi"})

    scheduler.register_handler(CompanionJobType.MOOD_UPDATE, _handler)
    chatbot_id = _make_chatbot()
    handle = scheduler.schedule(_request(chatbot_id, "key-exec"))

    outcomes = scheduler.run_due("worker-1")

    assert len(outcomes) == 1
    assert outcomes[0].status == JOB_SUCCEEDED
    assert executed == ["thunk"]
    assert arbitrated == [("llm", {"prompt": "hi"})]
    assert seen[0].job_id == handle.job_id
    assert seen[0].attempt == 1

    # The jobs module itself must not import any model, runtime, or
    # GPU surface: arbitration arrives only via injection above.
    jobs_source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "airunner_services"
        / "llm"
        / "companion"
        / "jobs.py"
    ).read_text()
    assert "import torch" not in jobs_source
    assert "from airunner_services.runtimes" not in jobs_source
    assert "RuntimeRegistry" not in jobs_source
    assert "model_manager" not in jobs_source


# --- Migration: fresh and historical SQLite fixtures ---


def test_fresh_sqlite_database_gets_companion_jobs_table(test_db) -> None:
    from sqlalchemy import inspect

    from airunner_services.database.db.engine import create_configured_engine

    engine = create_configured_engine(test_db)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert "companion_jobs" in tables


def test_historical_database_migrates_without_losing_existing_records(
    tmp_path, monkeypatch
) -> None:
    """A database at every pre-B06 head, without ``companion_jobs``,
    must gain that table on upgrade and keep every pre-existing row
    untouched -- the same stamp-based fixture approach as B02's
    migration test (replaying history from scratch is defeated by the
    initial migration's unconditional ``create_all``)."""
    from sqlalchemy import inspect
    from sqlalchemy.orm import sessionmaker

    from airunner_services.database.base import Base
    from airunner_services.database.db.engine import create_configured_engine

    db_models = importlib.import_module("airunner_services.database.models")
    assert db_models.CompanionJob.__tablename__ == "companion_jobs"

    db_path = tmp_path / "historical-b06.sqlite"
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
        pre_b06_tables = [
            table
            for name, table in Base.metadata.tables.items()
            if name != "companion_jobs"
        ]
        Base.metadata.create_all(bind=engine, tables=pre_b06_tables)
        command.stamp(alembic_cfg, _PRIOR_HEADS)

        pre_tables = set(inspect(engine).get_table_names())
        assert "companion_jobs" not in pre_tables

        Session = sessionmaker(bind=engine)
        with Session() as db:
            existing = Chatbot(name="pre-existing-b06-bot")
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
        assert "companion_jobs" in post_tables

        Session = sessionmaker(bind=engine)
        with Session() as db:
            row = db.query(Chatbot).filter(Chatbot.id == existing_id).one()
            assert row.name == "pre-existing-b06-bot"
    finally:
        engine.dispose()
        reset_engine()
