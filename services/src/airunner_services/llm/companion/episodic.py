"""Episodic session summaries (release issue B08).

The sweep fires one ``EPISODIC_SUMMARY`` job per inactive session;
the handler summarizes its completed turns only and persists the
result atomically. Import directly, never from ``__init__``
(SQLAlchemy, like ``repository.py``/``jobs.py``). No model, network,
or GPU I/O here; summarization uses the injected ``SummarizeFn``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.session import session_scope
from airunner_services.runtimes.contracts import ChatMessage, MessageRole

from .contracts import ChatbotId, SessionId
from .jobs import JobContext, JobHandler
from .memory_repository import SessionRecord, TurnRecord
from .repository import SqlCompanionMemoryRepository
from .scheduler import CompanionJobHandle, CompanionJobRequest
from .scheduler import CompanionJobType, CompanionScheduler

_SYSTEM_PROMPT = (
    "Summarize the completed conversation turns below into one short "
    "episodic memory paragraph: what happened, in order, with names, "
    "decisions, and open threads. Do not invent turns not shown."
)

# Gap-rotated spans stay small; newest rows win if one ever overflows.
_MAX_SUMMARY_TURNS = 1000

_ROLE_MAP: Dict[str, MessageRole] = {
    "system": MessageRole.SYSTEM,
    "user": MessageRole.USER,
    "assistant": MessageRole.ASSISTANT,
}


class EpisodicSummary(BaseModel):
    """One session's summarized episodic memory."""

    model_config = ConfigDict(extra="forbid")
    summary: str
    key_topics: List[str] = Field(default_factory=list)
    emotional_weight: Optional[float] = None


# May raise retryable CompanionError when inference is unavailable.
SummarizeFn = Callable[[JobContext, List[ChatMessage]], EpisodicSummary]


def is_completed_turn(turn: TurnRecord) -> bool:
    """True only for a fully persisted turn with real content."""
    if turn.turn_id is None or turn.turn_index is None:
        return False
    return bool(turn.content.strip())


def build_summary_prompt(turns: List[TurnRecord]) -> List[ChatMessage]:
    """Render completed turns as prompt messages, oldest first."""
    ordered = sorted(turns, key=lambda t: t.turn_index or 0)
    messages = [ChatMessage(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT)]
    for turn in ordered:
        role = _ROLE_MAP.get(turn.role)
        if role is not None:
            messages.append(ChatMessage(role=role, content=turn.content))
    return messages


def schedule_inactive_sessions(
    scheduler: CompanionScheduler,
    *,
    now: datetime,
    inactivity_gap: timedelta,
    limit: int = 25,
) -> List[CompanionJobHandle]:
    """Schedule one summary job per inactive, unsummarized session."""
    if limit <= 0:
        return []
    due = _due_sessions(now - inactivity_gap, limit)
    return [_schedule_one(scheduler, session) for session in due]


def _due_sessions(cutoff: datetime, limit: int) -> List[SessionRecord]:
    """Sessions idle since ``cutoff`` with no summary yet."""
    with session_scope() as db:
        rows = (
            db.query(CompanionSession)
            .filter(
                CompanionSession.summary_ready.is_(False),
                CompanionSession.last_message_at <= cutoff,
            )
            .order_by(CompanionSession.id)
            .limit(limit)
            .all()
        )
        return [_to_record(row) for row in rows]


def _schedule_one(
    scheduler: CompanionScheduler, session: SessionRecord
) -> CompanionJobHandle:
    """Enqueue one job pinned to the session's closing boundary."""
    assert session.session_id is not None  # stored rows have ids
    closed_at = session.last_message_at
    key = f"episodic:{session.session_id}:{closed_at}"
    mood = session.emotional_weight
    payload = {"closed_at": closed_at, "mood_snapshot": mood}
    return scheduler.schedule(
        CompanionJobRequest(
            job_type=CompanionJobType.EPISODIC_SUMMARY,
            chatbot_id=session.chatbot_id,
            session_id=session.session_id,
            idempotency_key=key,
            payload=payload,
        )
    )


def make_episodic_summary_handler(
    repository: SqlCompanionMemoryRepository,
    summarize: SummarizeFn,
) -> JobHandler:
    """Build the B06 handler executing ``EPISODIC_SUMMARY`` jobs."""
    return lambda context: _run_summary(repository, summarize, context)


def _run_summary(
    repository: SqlCompanionMemoryRepository,
    summarize: SummarizeFn,
    context: JobContext,
) -> None:
    """Summarize one session; nothing is written before inference."""
    if context.session_id is None:
        raise ValueError("episodic summary job has no session_id")
    current = _read_session(context.chatbot_id, context.session_id)
    if current is None or current.summary_ready:
        return
    _summarize_open_session(repository, summarize, context, current)


def _summarize_open_session(
    repository: SqlCompanionMemoryRepository,
    summarize: SummarizeFn,
    context: JobContext,
    current: SessionRecord,
) -> None:
    """Summarize an unready session; re-checks readiness pre-write."""
    assert context.session_id is not None  # guarded by _run_summary
    completed = _completed_turns(
        repository, context.chatbot_id, context.session_id
    )
    if not completed:
        repository.update_session_summary(_merged_record(current, None))
        return
    result = summarize(context, build_summary_prompt(completed))
    fresh = _read_session(context.chatbot_id, context.session_id)
    if fresh is None or fresh.summary_ready:
        return
    repository.update_session_summary(_merged_record(fresh, result))


def _completed_turns(
    repository: SqlCompanionMemoryRepository,
    chatbot_id: ChatbotId,
    session_id: SessionId,
) -> List[TurnRecord]:
    """One session's completed turns, oldest first."""
    turns = repository.get_recent_turns(
        chatbot_id, session_id, limit=_MAX_SUMMARY_TURNS
    )
    return [t for t in turns if is_completed_turn(t)]


def _read_session(
    chatbot_id: ChatbotId, session_id: SessionId
) -> Optional[SessionRecord]:
    """Fresh read of one session row, detached from any ORM session."""
    with session_scope() as db:
        row = (
            db.query(CompanionSession)
            .filter_by(id=int(session_id), chatbot_id=int(chatbot_id))
            .one_or_none()
        )
        return None if row is None else _to_record(row)


def _to_record(row: CompanionSession) -> SessionRecord:
    """Copy one live row into a detached record (call inside session)."""
    return SessionRecord(
        session_id=row.id,
        chatbot_id=row.chatbot_id,
        started_at=row.started_at.isoformat(),
        last_message_at=row.last_message_at.isoformat(),
        episodic_summary=row.episodic_summary,
        rolling_summary=row.rolling_summary,
        emotional_weight=row.emotional_weight,
        key_topics=list(row.key_topics or []),
        summary_ready=row.summary_ready,
    )


def _merged_record(
    current: SessionRecord, result: Optional[EpisodicSummary]
) -> SessionRecord:
    """Merge a result over stored fields B08 must not clobber."""
    weight, topics = _mood_and_topics(current, result)
    return SessionRecord(
        session_id=current.session_id,
        chatbot_id=current.chatbot_id,
        started_at=current.started_at,
        last_message_at=current.last_message_at,
        episodic_summary=(result.summary if result is not None else None),
        rolling_summary=current.rolling_summary,
        emotional_weight=weight,
        key_topics=topics,
        summary_ready=True,
    )


def _mood_and_topics(
    current: SessionRecord, result: Optional[EpisodicSummary]
) -> tuple[Optional[float], List[str]]:
    """Reported mood/topics win; stored values survive otherwise."""
    weight = current.emotional_weight
    topics = list(current.key_topics)
    if result is not None and result.emotional_weight is not None:
        weight = result.emotional_weight
    if result is not None and result.key_topics:
        topics = list(result.key_topics)
    return weight, topics


__all__ = [
    "EpisodicSummary",
    "SummarizeFn",
    "build_summary_prompt",
    "is_completed_turn",
    "make_episodic_summary_handler",
    "schedule_inactive_sessions",
]
