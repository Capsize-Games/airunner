"""Version-guarded narrative-memory updates (release issue B09).

Blends reviewed episodic summaries into B03's narrative row via a
stale-loss guarded write. No model, network, or GPU I/O here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, List, Optional, Tuple

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from airunner_services.database.models.companion_narrative import (
    CompanionNarrative,
)
from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.session import session_scope

from .contracts import ChatbotId, SessionId
from .jobs import JobContext, JobHandler
from .narrative import (
    MAX_NARRATIVE_CHARS,
    MAX_NARRATIVE_TOKENS,
    BlendFn,
    NarrativeSource,
    blend_sources,
    fit_to_budget,
    sanitize_memory_text,
)
from .repository import NarrativeRecord
from .scheduler import (
    CompanionJobHandle,
    CompanionJobRequest,
    CompanionJobType,
    CompanionScheduler,
)


def try_store_narrative(
    chatbot_id: ChatbotId,
    content: str,
    *,
    expected_version: int,
    clock: Callable[[], datetime] = datetime.utcnow,
) -> Optional[NarrativeRecord]:
    """Store one narrative iff its version still matches (None if
    a concurrent writer moved past ``expected_version``)."""
    now = clock()
    with session_scope() as db:
        return _store_in(db, chatbot_id, content, expected_version, now)


def _store_in(
    db, chatbot_id: ChatbotId, content: str, expected: int, now: datetime
) -> Optional[NarrativeRecord]:
    """Insert at version 1, or guarded-rewrite ``expected``."""
    row = _find_narrative(db, chatbot_id)
    if row is None:
        if expected != 0:
            return None
        return _insert_first(db, chatbot_id, content, now)
    if row.version != expected:
        return None
    return _update_guarded(db, chatbot_id, content, expected, now)


def _find_narrative(db, chatbot_id: ChatbotId) -> Optional[CompanionNarrative]:
    """One chatbot's narrative row, or None when never written."""
    return (
        db.query(CompanionNarrative)
        .filter(CompanionNarrative.chatbot_id == int(chatbot_id))
        .one_or_none()
    )


def _update_guarded(
    db, chatbot_id: ChatbotId, content: str, expected: int, now: datetime
) -> Optional[NarrativeRecord]:
    """Rewrite version ``expected``; None when a race won first."""
    result = db.execute(
        update(CompanionNarrative)
        .where(
            CompanionNarrative.chatbot_id == int(chatbot_id),
            CompanionNarrative.version == expected,
        )
        .values(content=content, version=expected + 1, updated_at=now)
    )
    if result.rowcount != 1:
        return None
    return _to_record(db, chatbot_id)


def _insert_first(
    db, chatbot_id: ChatbotId, content: str, now: datetime
) -> Optional[NarrativeRecord]:
    """Insert version 1; a concurrent first write wins instead."""
    row = CompanionNarrative(
        chatbot_id=int(chatbot_id),
        content=content,
        version=1,
        created_at=now,
        updated_at=now,
    )
    savepoint = db.begin_nested()
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        savepoint.rollback()
        return None
    return _row_to_record(row)


def _to_record(db, chatbot_id: ChatbotId) -> NarrativeRecord:
    """Re-read the just-updated row detached from the session."""
    row = (
        db.query(CompanionNarrative)
        .filter(CompanionNarrative.chatbot_id == int(chatbot_id))
        .one()
    )
    return _row_to_record(row)


def _row_to_record(row: CompanionNarrative) -> NarrativeRecord:
    """Copy one live row into a detached record (call in session)."""
    return NarrativeRecord(
        narrative_id=row.id,
        chatbot_id=row.chatbot_id,
        content=row.content,
        version=row.version,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


def schedule_memory_blend(
    scheduler: CompanionScheduler,
    *,
    chatbot_id: ChatbotId,
    session_id: SessionId,
    expected_version: int,
    closed_at: str,
) -> CompanionJobHandle:
    """Schedule one blend keyed to the session's closing boundary."""
    return scheduler.schedule(
        CompanionJobRequest(
            job_type=CompanionJobType.MEMORY_BLEND,
            chatbot_id=chatbot_id,
            session_id=session_id,
            idempotency_key=f"blend:{session_id}:{closed_at}",
            payload={"expected_version": expected_version},
        )
    )


def make_memory_blend_handler(
    blend: BlendFn,
    *,
    clock: Callable[[], datetime] = datetime.utcnow,
) -> JobHandler:
    """Build the B06 handler executing ``MEMORY_BLEND`` jobs."""
    return lambda context: _run_blend(blend, clock, context)


def _run_blend(
    blend: BlendFn, clock: Callable[[], datetime], context: JobContext
) -> None:
    """Blend one reviewed episodic summary into the narrative."""
    if context.session_id is None:
        raise ValueError("memory blend job has no session_id")
    pending = _pending_blend(context)
    if pending is None:
        return
    base, sources = pending
    result = blend(context, sources)
    _store_blend(clock, context.chatbot_id, base, result.content)


def _pending_blend(
    context: JobContext,
) -> Optional[Tuple[int, List[NarrativeSource]]]:
    """Base version plus blend inputs, or None when no work remains."""
    assert context.session_id is not None  # guarded by _run_blend
    session_id = context.session_id
    summary = _reviewed_summary(context.chatbot_id, session_id)
    if summary is None:
        return None
    current = _read_narrative(context.chatbot_id)
    base = 0 if current is None else current.version
    if context.payload.get("expected_version", base) != base:
        return None
    return base, blend_sources(current, session_id, summary)


def _store_blend(
    clock: Callable[[], datetime],
    chatbot_id: ChatbotId,
    base: int,
    raw: str,
) -> None:
    """Sanitize, fit, and guarded-store one blend result."""
    content = fit_to_budget(
        sanitize_memory_text(raw),
        MAX_NARRATIVE_CHARS,
        MAX_NARRATIVE_TOKENS,
    )
    final = _read_narrative(chatbot_id)
    final_base = 0 if final is None else final.version
    if final_base != base:
        return
    try_store_narrative(
        chatbot_id, content, expected_version=base, clock=clock
    )


def _reviewed_summary(
    chatbot_id: ChatbotId, session_id: SessionId
) -> Optional[str]:
    """The session's episodic text, or None unless reviewed/ready."""
    with session_scope() as db:
        row = (
            db.query(CompanionSession)
            .filter_by(id=int(session_id), chatbot_id=int(chatbot_id))
            .one_or_none()
        )
        if row is None or not row.summary_ready:
            return None
        if row.episodic_summary is None or not row.episodic_summary.strip():
            return None
        return row.episodic_summary


def _read_narrative(chatbot_id: ChatbotId) -> Optional[NarrativeRecord]:
    """Fresh read of one narrative row, detached from any session."""
    with session_scope() as db:
        row = _find_narrative(db, chatbot_id)
        return None if row is None else _row_to_record(row)


__all__ = [
    "make_memory_blend_handler",
    "schedule_memory_blend",
    "try_store_narrative",
]
