"""Regression tests for release issue B08.

Proves episodic session summaries satisfy B08's acceptance criteria:

- Fake-clock session closure yields one summary with correct source
  scope (the closed session only; the rotated-to session is clean).
- Retry/restart does not duplicate or overwrite newer session data
  (failed inference writes nothing; redelivery after readiness is a
  no-op; the closing-boundary idempotency key dedups rescheduling).
- Incomplete turns and another bot's history never enter the prompt.

Also proves the mechanism: inactive-only scheduling, empty sessions
marked ready without an inference call, atomic single-write
persistence, and preservation of the rolling summary, mood snapshot,
and stored topics the summarizer does not replace.

Uses only temporary, explicit SQLite databases (never the owner's
active environment), a fake clock, and fake summarizers -- no real
model, network, GPU, or GUI access.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta
from typing import List

import pytest

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.companion_job import CompanionJob
from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.session import reset_engine, session_scope
from airunner_services.database.setup_database import setup_database
from airunner_services.llm.companion.contracts import (
    ERROR_INFERENCE_UNAVAILABLE,
    CallChainId,
    ChatbotId,
    CompanionError,
    CompanionErrorCode,
    SessionId,
)
from airunner_services.llm.companion.episodic import (
    EpisodicSummary,
    build_summary_prompt,
    is_completed_turn,
    make_episodic_summary_handler,
    schedule_inactive_sessions,
)
from airunner_services.llm.companion.jobs import (
    JOB_QUEUED,
    DurableCompanionScheduler,
    JobContext,
)
from airunner_services.llm.companion.memory_repository import (
    SessionRecord,
    TurnRecord,
)
from airunner_services.llm.companion.repository import (
    SqlCompanionMemoryRepository,
)
from airunner_services.llm.companion.scheduler import CompanionJobType
from airunner_services.runtimes.contracts import ChatMessage

_GAP = timedelta(hours=4)

_chatbot_counter = itertools.count()
_chain_counter = itertools.count()


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'release-b08.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    yield db_url
    reset_engine()


@pytest.fixture()
def fake_clock():
    """A controllable clock: advance ``fake_clock.now`` directly."""

    class _FakeClock:
        def __init__(self) -> None:
            self.now = datetime(2026, 1, 1, 12, 0, 0)

        def __call__(self) -> datetime:
            return self.now

    return _FakeClock()


@pytest.fixture()
def repository(fake_clock):
    return SqlCompanionMemoryRepository(clock=fake_clock)


@pytest.fixture()
def scheduler(fake_clock):
    return DurableCompanionScheduler(clock=fake_clock)


class _FakeSummarizer:
    """Records prompts; fails until ``failures_left`` hits zero."""

    def __init__(self, failures_left: int = 0) -> None:
        self.failures_left = failures_left
        self.calls: List[List[ChatMessage]] = []

    def __call__(
        self, context: JobContext, messages: List[ChatMessage]
    ) -> EpisodicSummary:
        self.calls.append(list(messages))
        if self.failures_left > 0:
            self.failures_left -= 1
            raise CompanionError(
                CompanionErrorCode(
                    code=ERROR_INFERENCE_UNAVAILABLE,
                    detail="inference offline in test",
                    retryable=True,
                )
            )
        bodies = [m.content for m in messages if m.role != "system"]
        return EpisodicSummary(summary=f"SUMMARY:{'|'.join(bodies)}")


def _make_chatbot() -> ChatbotId:
    with session_scope() as db:
        index = next(_chatbot_counter)
        chatbot = Chatbot(name=f"b08-bot-{index}")
        db.add(chatbot)
        db.flush()
        return ChatbotId(chatbot.id)


def _start_session(repository, chatbot_id: ChatbotId) -> SessionId:
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    return session.session_id


def _append(
    repository,
    chatbot_id: ChatbotId,
    session_id: SessionId,
    role: str,
    content: str,
) -> TurnRecord:
    return repository.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session_id,
            role=role,
            content=content,
            call_chain_id=CallChainId(f"b08-chain-{next(_chain_counter)}"),
        )
    )


def _read_session(session_id: SessionId) -> CompanionSession:
    with session_scope() as db:
        row = (
            db.query(CompanionSession)
            .filter(CompanionSession.id == int(session_id))
            .one()
        )
        db.expunge(row)
        return row


def _job_count(chatbot_id: ChatbotId) -> int:
    with session_scope() as db:
        return (
            db.query(CompanionJob)
            .filter(CompanionJob.chatbot_id == int(chatbot_id))
            .count()
        )


def test_closure_yields_one_summary_on_closed_session(
    test_db, repository, scheduler, fake_clock
):
    bot = _make_chatbot()
    session_id = _start_session(repository, bot)
    _append(repository, bot, session_id, "user", "alpha first")
    _append(repository, bot, session_id, "assistant", "alpha reply")

    assert (
        schedule_inactive_sessions(
            scheduler, now=fake_clock.now, inactivity_gap=_GAP
        )
        == []
    )

    fake_clock.now += timedelta(hours=5)
    handles = schedule_inactive_sessions(
        scheduler, now=fake_clock.now, inactivity_gap=_GAP
    )
    assert len(handles) == 1
    assert handles[0].accepted is True
    assert handles[0].job_type == CompanionJobType.EPISODIC_SUMMARY

    fake = _FakeSummarizer()
    scheduler.register_handler(
        CompanionJobType.EPISODIC_SUMMARY,
        make_episodic_summary_handler(repository, fake),
    )
    outcomes = scheduler.run_due("b08-worker")
    assert len(outcomes) == 1
    assert outcomes[0].status == "succeeded"

    assert len(fake.calls) == 1
    bodies = [m.content for m in fake.calls[0] if m.role != "system"]
    assert bodies == ["alpha first", "alpha reply"]

    closed = _read_session(session_id)
    assert closed.summary_ready is True
    assert closed.episodic_summary == "SUMMARY:alpha first|alpha reply"

    # The gap rotated: active chat moved to a fresh, clean session.
    fresh_id = _start_session(repository, bot)
    assert fresh_id != session_id
    fresh = _read_session(fresh_id)
    assert fresh.summary_ready is False
    assert fresh.episodic_summary is None


def test_retry_then_restart_writes_once(
    test_db, repository, scheduler, fake_clock
):
    bot = _make_chatbot()
    session_id = _start_session(repository, bot)
    _append(repository, bot, session_id, "user", "retry me")

    fake_clock.now += timedelta(hours=5)
    handles = schedule_inactive_sessions(
        scheduler, now=fake_clock.now, inactivity_gap=_GAP
    )
    assert len(handles) == 1

    fake = _FakeSummarizer(failures_left=1)
    scheduler.register_handler(
        CompanionJobType.EPISODIC_SUMMARY,
        make_episodic_summary_handler(repository, fake),
    )
    outcomes = scheduler.run_due("b08-worker")
    assert outcomes[0].status == JOB_QUEUED

    # Atomic: the failed attempt wrote nothing at all.
    pending = _read_session(session_id)
    assert pending.summary_ready is False
    assert pending.episodic_summary is None

    # Active chat is unaffected by the queued retry.
    stored = _append(repository, bot, session_id, "user", "still here")
    assert stored.turn_id is not None

    # A restarted process picks the job up and finishes it exactly once.
    fake_clock.now += timedelta(hours=1)
    restarted = DurableCompanionScheduler(clock=fake_clock)
    restarted.register_handler(
        CompanionJobType.EPISODIC_SUMMARY,
        make_episodic_summary_handler(repository, fake),
    )
    outcomes = restarted.run_due("b08-worker-2")
    assert outcomes[0].status == "succeeded"
    assert len(fake.calls) == 2  # one failure, one success

    done = _read_session(session_id)
    assert done.summary_ready is True
    assert done.episodic_summary is not None

    # Rescheduling the same closing boundary is a duplicate no-op.
    repeat = schedule_inactive_sessions(
        scheduler, now=fake_clock.now, inactivity_gap=_GAP
    )
    assert repeat == []
    assert _job_count(bot) == 1


def test_redelivery_never_overwrites_ready_session(
    test_db, repository, scheduler, fake_clock
):
    bot = _make_chatbot()
    session_id = _start_session(repository, bot)
    _append(repository, bot, session_id, "user", "already done")

    stored = _read_session(session_id)
    repository.update_session_summary(
        SessionRecord(
            session_id=session_id,
            chatbot_id=bot,
            started_at=stored.started_at.isoformat(),
            last_message_at=stored.last_message_at.isoformat(),
            episodic_summary="NEWER-SUMMARY",
            rolling_summary="ROLLING",
            emotional_weight=0.25,
            key_topics=["kept"],
            summary_ready=True,
        )
    )

    fake = _FakeSummarizer()
    handler = make_episodic_summary_handler(repository, fake)
    handler(
        JobContext(
            job_id="999",
            job_type=CompanionJobType.EPISODIC_SUMMARY,
            chatbot_id=bot,
            session_id=session_id,
        )
    )

    assert fake.calls == []
    current = _read_session(session_id)
    assert current.episodic_summary == "NEWER-SUMMARY"
    assert current.rolling_summary == "ROLLING"
    assert current.emotional_weight == 0.25
    assert list(current.key_topics or []) == ["kept"]


def test_write_preserves_unreported_fields(
    test_db, repository, scheduler, fake_clock
):
    bot = _make_chatbot()
    session_id = _start_session(repository, bot)
    _append(repository, bot, session_id, "user", "preserve me")

    stored = _read_session(session_id)
    repository.update_session_summary(
        SessionRecord(
            session_id=session_id,
            chatbot_id=bot,
            started_at=stored.started_at.isoformat(),
            last_message_at=stored.last_message_at.isoformat(),
            rolling_summary="ROLLING",
            emotional_weight=0.5,
            key_topics=["mood-topic"],
        )
    )

    fake_clock.now += timedelta(hours=5)
    schedule_inactive_sessions(
        scheduler, now=fake_clock.now, inactivity_gap=_GAP
    )
    fake = _FakeSummarizer()
    scheduler.register_handler(
        CompanionJobType.EPISODIC_SUMMARY,
        make_episodic_summary_handler(repository, fake),
    )
    scheduler.run_due("b08-worker")

    current = _read_session(session_id)
    assert current.summary_ready is True
    assert current.episodic_summary is not None
    assert current.rolling_summary == "ROLLING"
    assert current.emotional_weight == 0.5
    assert list(current.key_topics or []) == ["mood-topic"]


def test_prompt_excludes_incomplete_and_foreign_turns(
    test_db, repository, scheduler, fake_clock
):
    bot_a = _make_chatbot()
    session_a = _start_session(repository, bot_a)
    _append(repository, bot_a, session_a, "user", "a first")
    _append(repository, bot_a, session_a, "assistant", "a reply")
    _append(repository, bot_a, session_a, "user", "   \n  ")

    bot_b = _make_chatbot()
    session_b = _start_session(repository, bot_b)
    _append(repository, bot_b, session_b, "user", "FOREIGN-MARKER")

    fake_clock.now += timedelta(hours=5)
    handles = schedule_inactive_sessions(
        scheduler, now=fake_clock.now, inactivity_gap=_GAP
    )
    assert len(handles) == 2

    seen = {}

    def _scoped(context: JobContext, messages):
        bodies = [m.content for m in messages if m.role != "system"]
        seen[int(context.chatbot_id)] = bodies
        return EpisodicSummary(summary="SUMMARY")

    scheduler.register_handler(
        CompanionJobType.EPISODIC_SUMMARY,
        make_episodic_summary_handler(repository, _scoped),
    )
    scheduler.run_due("b08-worker", limit=2)

    assert seen[int(bot_a)] == ["a first", "a reply"]
    assert seen[int(bot_b)] == ["FOREIGN-MARKER"]

    # Unit shape: unstored or content-free turns are incomplete, and
    # unknown roles never reach the model even if stored somehow.
    good = TurnRecord(
        turn_id=1,
        chatbot_id=bot_a,
        session_id=session_a,
        role="user",
        content="ok",
        turn_index=0,
        call_chain_id=CallChainId("u1"),
    )
    assert is_completed_turn(good) is True
    no_id = good.model_copy(update={"turn_id": None})
    assert is_completed_turn(no_id) is False
    no_index = good.model_copy(update={"turn_index": None})
    assert is_completed_turn(no_index) is False
    blank = good.model_copy(update={"content": "  "})
    assert is_completed_turn(blank) is False
    weird = good.model_copy(update={"role": "carrier-pigeon"})
    assert [m.role for m in build_summary_prompt([weird])] == ["system"]


def test_empty_session_marked_ready_without_inference(
    test_db, repository, scheduler, fake_clock
):
    bot = _make_chatbot()
    session_id = _start_session(repository, bot)

    fake_clock.now += timedelta(hours=5)
    handles = schedule_inactive_sessions(
        scheduler, now=fake_clock.now, inactivity_gap=_GAP
    )
    assert len(handles) == 1

    fake = _FakeSummarizer()
    scheduler.register_handler(
        CompanionJobType.EPISODIC_SUMMARY,
        make_episodic_summary_handler(repository, fake),
    )
    outcomes = scheduler.run_due("b08-worker")
    assert outcomes[0].status == "succeeded"

    assert fake.calls == []
    current = _read_session(session_id)
    assert current.summary_ready is True
    assert current.episodic_summary is None

    # ... and a ready session is never scheduled again.
    assert (
        schedule_inactive_sessions(
            scheduler, now=fake_clock.now, inactivity_gap=_GAP
        )
        == []
    )


def test_handler_ignores_unknown_session(
    test_db, repository, scheduler, fake_clock
):
    bot = _make_chatbot()
    fake = _FakeSummarizer()
    handler = make_episodic_summary_handler(repository, fake)
    handler(
        JobContext(
            job_id="404",
            job_type=CompanionJobType.EPISODIC_SUMMARY,
            chatbot_id=bot,
            session_id=SessionId(424242),
        )
    )
    assert fake.calls == []
