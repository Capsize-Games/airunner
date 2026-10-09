"""Regression tests for release issue B07.

Proves post-turn fact extraction and deduplication satisfy B07's
acceptance criteria:

- Neutral fixtures cover new facts, duplicate facts, corrections,
  and retractions.
- A malformed response or job retry cannot corrupt or duplicate
  memory (schema validation before any write; per-event idempotency
  keys; retract-before-save corrections).
- Every inference task routes through the injected local provider
  entry point with a bounded budget (the fake asserts it observes
  the wired ``arbitrate`` callable and a budget-capped prompt).

Uses only temporary, explicit SQLite databases (never the owner's
active environment), a fake clock, and fake extractors -- no real
model, network, GPU, or GUI access.
"""

from __future__ import annotations

import itertools
from datetime import datetime
from typing import List

import pytest

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.session import reset_engine, session_scope
from airunner_services.database.setup_database import setup_database
from airunner_services.llm.companion.contracts import (
    CallChainId,
    ChatbotId,
    ContextBudget,
    SessionId,
)
from airunner_services.llm.companion.fact_extraction import (
    ExtractedFact,
    ExtractionResult,
    build_extraction_prompt,
    is_same_fact,
    is_supported,
    make_fact_extraction_handler,
    normalize_fact_text,
    schedule_fact_extraction,
)
from airunner_services.llm.companion.jobs import (
    JOB_FAILED,
    JOB_QUEUED,
    JOB_SUCCEEDED,
    DurableCompanionScheduler,
    JobContext,
)
from airunner_services.llm.companion.memory_repository import TurnRecord
from airunner_services.llm.companion.repository import (
    SqlCompanionMemoryRepository,
)
from airunner_services.llm.companion.scheduler import CompanionJobType
from airunner_services.runtimes.contracts import ChatMessage

_chatbot_counter = itertools.count()
_chain_counter = itertools.count()


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'release-b07.sqlite'}"
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
    arbitrate_calls: List[str] = []

    def _arbitrate(prompt: str) -> str:
        arbitrate_calls.append(prompt)
        return "local"

    produced = DurableCompanionScheduler(
        clock=fake_clock, arbitrate=_arbitrate
    )
    produced.test_calls = arbitrate_calls  # type: ignore[attr-defined]
    return produced


def _make_chatbot() -> ChatbotId:
    with session_scope() as db:
        index = next(_chatbot_counter)
        row = Chatbot(name=f"b07-bot-{index}")
        db.add(row)
        db.flush()
        return ChatbotId(row.id)


def _append_pair(repository, chatbot_id, session_id):
    """One synthetic user + assistant turn about a library."""
    user = repository.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session_id,
            role="user",
            content="Does the downtown library lend telescopes?",
            call_chain_id=CallChainId(f"b07-{next(_chain_counter)}"),
        )
    )
    assistant = repository.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session_id,
            role="assistant",
            content=(
                "Yes, the downtown library lends telescopes " "for two weeks."
            ),
            call_chain_id=CallChainId(f"b07-{next(_chain_counter)}"),
        )
    )
    return user, assistant


class _FakeExtractor:
    """Returns a canned result; asserts the local-provider wiring."""

    def __init__(self, result, *, scheduler=None) -> None:
        self.result = result
        self.calls: List[List[ChatMessage]] = []
        self.scheduler = scheduler

    def __call__(self, context: JobContext, messages: List[ChatMessage]):
        self.calls.append(list(messages))
        assert context.job_type is CompanionJobType.FACT_EXTRACTION
        assert callable(context.arbitrate)
        context.arbitrate("extract")
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _run_turn(scheduler, handler, chatbot_id, session, turn):
    """Schedule and run one extraction for one stored turn."""
    assert session.session_id is not None
    assert turn.turn_id is not None
    scheduler.register_handler(CompanionJobType.FACT_EXTRACTION, handler)
    handle = schedule_fact_extraction(
        scheduler,
        chatbot_id=chatbot_id,
        session_id=session.session_id,
        turn_id=int(turn.turn_id),
    )
    assert handle.accepted
    outcomes = scheduler.run_due("b07-worker", limit=4)
    assert len(outcomes) == 1
    return outcomes[0]


def test_new_fact_is_saved(test_db, repository, scheduler):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    _, assistant = _append_pair(repository, chatbot_id, session.session_id)
    assert assistant.turn_id is not None
    fake = _FakeExtractor(
        ExtractionResult(
            facts=[
                ExtractedFact(
                    content="the downtown library lends telescopes",
                    subject="world",
                )
            ]
        ),
        scheduler=scheduler,
    )
    handler = make_fact_extraction_handler(repository, fake)
    outcome = _run_turn(scheduler, handler, chatbot_id, session, assistant)
    assert outcome.status == JOB_SUCCEEDED
    assert len(fake.calls) == 1
    rows = repository.get_facts(chatbot_id, limit=10)
    assert [r.content for r in rows] == [
        "the downtown library lends telescopes"
    ]


def test_duplicate_fact_is_not_stored_twice(test_db, repository, scheduler):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    _, assistant = _append_pair(repository, chatbot_id, session.session_id)
    assert assistant.turn_id is not None
    result = ExtractionResult(
        facts=[ExtractedFact(content="the downtown library lends telescopes")]
    )
    handler = make_fact_extraction_handler(
        repository, _FakeExtractor(result, scheduler=scheduler)
    )
    first = _run_turn(scheduler, handler, chatbot_id, session, assistant)
    assert first.status == JOB_SUCCEEDED
    # A paraphrase of the stored fact in a later turn is a duplicate.
    later = repository.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session.session_id,
            role="assistant",
            content="As I said, telescopes are lent by the downtown library.",
            call_chain_id=CallChainId(f"b07-{next(_chain_counter)}"),
        )
    )
    assert later.turn_id is not None
    paraphrase = ExtractionResult(
        facts=[ExtractedFact(content="downtown library lends telescopes")]
    )
    handler = make_fact_extraction_handler(
        repository, _FakeExtractor(paraphrase, scheduler=scheduler)
    )
    second = _run_turn(scheduler, handler, chatbot_id, session, later)
    assert second.status == JOB_SUCCEEDED
    rows = repository.get_facts(chatbot_id, limit=10)
    assert len(rows) == 1


def test_correction_retracts_old_and_saves_new(test_db, repository, scheduler):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    _, assistant = _append_pair(repository, chatbot_id, session.session_id)
    assert assistant.turn_id is not None
    seed = ExtractionResult(
        facts=[ExtractedFact(content="the downtown library lends telescopes")]
    )
    handler = make_fact_extraction_handler(
        repository, _FakeExtractor(seed, scheduler=scheduler)
    )
    _run_turn(scheduler, handler, chatbot_id, session, assistant)
    # The user corrects the loan period; the extractor retracts the
    # stale fact and saves the corrected one in the same event.
    fix = repository.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session.session_id,
            role="user",
            content="Actually the loan period is three weeks, not two.",
            call_chain_id=CallChainId(f"b07-{next(_chain_counter)}"),
        )
    )
    assert fix.turn_id is not None
    correction = ExtractionResult(
        facts=[
            ExtractedFact(
                action="retract",
                content="the downtown library lends telescopes",
            ),
            ExtractedFact(
                content="the downtown library lends telescopes for three weeks"
            ),
        ]
    )
    handler = make_fact_extraction_handler(
        repository, _FakeExtractor(correction, scheduler=scheduler)
    )
    outcome = _run_turn(scheduler, handler, chatbot_id, session, fix)
    assert outcome.status == JOB_SUCCEEDED
    active = repository.get_facts(chatbot_id, limit=10)
    assert [r.content for r in active] == [
        "the downtown library lends telescopes for three weeks"
    ]
    stashed = repository.get_facts(
        chatbot_id, limit=10, include_retracted=True
    )
    assert len(stashed) == 2


def test_retraction_without_match_is_a_noop(test_db, repository, scheduler):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    _, assistant = _append_pair(repository, chatbot_id, session.session_id)
    assert assistant.turn_id is not None
    result = ExtractionResult(
        facts=[
            ExtractedFact(action="retract", content="a fact never stored here")
        ]
    )
    handler = make_fact_extraction_handler(
        repository, _FakeExtractor(result, scheduler=scheduler)
    )
    outcome = _run_turn(scheduler, handler, chatbot_id, session, assistant)
    assert outcome.status == JOB_SUCCEEDED
    assert repository.get_facts(chatbot_id, limit=10) == []


def test_unsupported_invented_fact_is_rejected(test_db, repository, scheduler):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    _, assistant = _append_pair(repository, chatbot_id, session.session_id)
    assert assistant.turn_id is not None
    result = ExtractionResult(
        facts=[
            ExtractedFact(content="the downtown library lends telescopes"),
            ExtractedFact(content="the user owns a parrot named Biscuit"),
        ]
    )
    handler = make_fact_extraction_handler(
        repository, _FakeExtractor(result, scheduler=scheduler)
    )
    outcome = _run_turn(scheduler, handler, chatbot_id, session, assistant)
    assert outcome.status == JOB_SUCCEEDED
    rows = repository.get_facts(chatbot_id, limit=10)
    assert [r.content for r in rows] == [
        "the downtown library lends telescopes"
    ]


def test_malformed_response_writes_nothing(test_db, repository, scheduler):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    _, assistant = _append_pair(repository, chatbot_id, session.session_id)
    assert assistant.turn_id is not None
    handler = make_fact_extraction_handler(
        repository,
        _FakeExtractor({"facts": [{"content": 42}]}, scheduler=scheduler),
    )
    outcome = _run_turn(scheduler, handler, chatbot_id, session, assistant)
    assert outcome.status == JOB_QUEUED
    assert outcome.error is not None
    assert repository.get_facts(chatbot_id, limit=10) == []


def test_job_retry_does_not_duplicate_memory(test_db, repository, fake_clock):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    _, assistant = _append_pair(repository, chatbot_id, session.session_id)
    assert assistant.turn_id is not None
    flaky = _FakeExtractor(
        ExtractionResult(
            facts=[
                ExtractedFact(content="the downtown library lends telescopes")
            ]
        )
    )
    worker = DurableCompanionScheduler(
        clock=fake_clock, arbitrate=lambda *args: None
    )
    handler = make_fact_extraction_handler(repository, flaky)
    worker.register_handler(CompanionJobType.FACT_EXTRACTION, handler)
    first = schedule_fact_extraction(
        worker,
        chatbot_id=chatbot_id,
        session_id=session.session_id,
        turn_id=int(assistant.turn_id),
    )
    assert first.accepted
    # Rescheduling the same turn is a duplicate, not a second job.
    again = schedule_fact_extraction(
        worker,
        chatbot_id=chatbot_id,
        session_id=session.session_id,
        turn_id=int(assistant.turn_id),
    )
    assert again.accepted is False
    assert again.reason == "duplicate"
    assert worker.run_due("b07-worker", limit=4)[0].status == JOB_SUCCEEDED
    # Redelivering the handler for the same job cannot duplicate it.
    context = JobContext(
        job_id=first.job_id,
        job_type=CompanionJobType.FACT_EXTRACTION,
        chatbot_id=chatbot_id,
        session_id=session.session_id,
        payload={"turn_id": int(assistant.turn_id)},
        attempt=2,
        arbitrate=lambda *args: None,
    )
    handler(context)
    rows = repository.get_facts(chatbot_id, limit=10)
    assert len(rows) == 1


def test_inference_goes_through_arbitrate_within_budget(
    test_db, repository, scheduler
):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    _, assistant = _append_pair(repository, chatbot_id, session.session_id)
    assert assistant.turn_id is not None
    budget = ContextBudget(
        max_prompt_tokens=64, max_recent_turns=2, max_facts=1
    )
    fake = _FakeExtractor(ExtractionResult(facts=[]), scheduler=scheduler)
    handler = make_fact_extraction_handler(repository, fake, budget=budget)
    outcome = _run_turn(scheduler, handler, chatbot_id, session, assistant)
    assert outcome.status == JOB_SUCCEEDED
    assert scheduler.test_calls == ["extract"]
    prompt = fake.calls[0]
    bodies = [m.content for m in prompt if m.role != "system"]
    assert len(bodies) <= budget.max_recent_turns
    assert all(body.strip() for body in bodies)
    variable = [m.content for m in prompt[1:]]
    assert sum(len(part) for part in variable) <= (
        budget.max_prompt_tokens * 4
    )


def test_prompt_builder_respects_budget():
    budget = ContextBudget(
        max_prompt_tokens=8, max_recent_turns=1, max_facts=0
    )
    turns = [
        TurnRecord(
            turn_id=i + 1,
            chatbot_id=ChatbotId(1),
            session_id=SessionId(1),
            role="user",
            content="word " * 100,
            turn_index=i,
            call_chain_id=CallChainId("b07"),
        )
        for i in range(4)
    ]
    messages = build_extraction_prompt(turns, [], budget)
    bodies = [m.content for m in messages if m.role != "system"]
    assert len(bodies) == 1
    variable = [m.content for m in messages[1:]]
    assert sum(len(part) for part in variable) <= 8 * 4


def test_matching_helpers_reject_noise_and_catch_dupes():
    assert normalize_fact_text("  The Library, LENDS Telescopes! ") == (
        "the library lends telescopes"
    )
    assert is_supported(
        "the library lends telescopes",
        "Yes, the downtown library lends telescopes for two weeks.",
    )
    assert not is_supported(
        "the user owns a parrot named Biscuit",
        "Yes, the downtown library lends telescopes for two weeks.",
    )
    assert is_same_fact(
        "the downtown library lends telescopes",
        "The downtown library lends telescopes!",
    )
    assert not is_same_fact(
        "the downtown library lends telescopes",
        "the user owns a parrot named Biscuit",
    )


def test_missing_turn_writes_nothing(test_db, repository, scheduler):
    chatbot_id = _make_chatbot()
    session = repository.get_or_start_session(chatbot_id)
    assert session.session_id is not None
    fake = _FakeExtractor(ExtractionResult(facts=[]), scheduler=scheduler)
    handler = make_fact_extraction_handler(repository, fake)
    scheduler.register_handler(CompanionJobType.FACT_EXTRACTION, handler)
    handle = schedule_fact_extraction(
        scheduler,
        chatbot_id=chatbot_id,
        session_id=session.session_id,
        turn_id=9999,
    )
    assert handle.accepted
    outcome = scheduler.run_due("b07-worker", limit=4)[0]
    assert outcome.status == JOB_SUCCEEDED
    assert fake.calls == []
    assert repository.get_facts(chatbot_id, limit=10) == []
