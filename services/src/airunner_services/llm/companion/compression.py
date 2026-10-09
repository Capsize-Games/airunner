"""Rolling context compression without deleting history (B09).

Compresses one session's recent turns into its ``rolling_summary`` so
prompt assembly (B10) can stay within budget. The write is
base-guarded: a job whose base rolling text no longer matches the
stored one is stale and writes nothing. Only the summary column is
ever updated -- original turns stay persisted and retrievable.

Import directly, never from ``__init__`` (SQLAlchemy, like
``episodic.py``). No model, network, or GPU I/O here; compression
uses the injected ``CompressFn``.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Update, update
from sqlalchemy.sql.elements import ColumnElement

from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.session import session_scope
from airunner_services.runtimes.contracts import (
    ChatMessage,
    MessageRole,
)

from .contracts import ChatbotId, SessionId
from .episodic import build_summary_prompt, is_completed_turn
from .jobs import JobContext, JobHandler
from .memory_repository import TurnRecord
from .narrative import fit_to_budget, sanitize_memory_text
from .repository import SqlCompanionMemoryRepository
from .scheduler import (
    CompanionJobHandle,
    CompanionJobRequest,
    CompanionJobType,
    CompanionScheduler,
)

# Explicit budgets: the stored rolling summary never exceeds either
# bound, whatever the compress function returns.
MAX_ROLLING_CHARS = 2000
MAX_ROLLING_TOKENS = 500

# Gap-rotated spans stay small; newest rows win if one ever overflows.
_MAX_COMPRESS_TURNS = 1000

_SYSTEM_PROMPT = (
    "Compress the conversation turns below into a short rolling "
    "context paragraph: who, what was decided, and open threads. "
    "Do not invent turns not shown."
)


class RollingResult(BaseModel):
    """One compressed rolling context with its coverage and size."""

    model_config = ConfigDict(extra="forbid")

    content: str
    turns_covered: int = 0
    char_count: int = 0
    token_estimate: int = 0


# May raise retryable CompanionError when inference is unavailable.
CompressFn = Callable[[JobContext, List[ChatMessage]], RollingResult]


def build_rolling_prompt(
    turns: List[TurnRecord], base_rolling: Optional[str]
) -> List[ChatMessage]:
    """Turn messages plus the previous rolling context, oldest first."""
    system = _SYSTEM_PROMPT
    if base_rolling is not None and base_rolling.strip():
        system += f"\nPrevious compressed context:\n{base_rolling.strip()}"
    messages = build_summary_prompt(turns)
    messages[0] = ChatMessage(role=MessageRole.SYSTEM, content=system)
    return messages


def schedule_rolling_compression(
    scheduler: CompanionScheduler,
    *,
    chatbot_id: ChatbotId,
    session_id: SessionId,
    base_rolling: Optional[str],
    boundary_turn_index: int,
) -> CompanionJobHandle:
    """Schedule one compression pinned to a turn-index boundary."""
    return scheduler.schedule(
        CompanionJobRequest(
            job_type=CompanionJobType.ROLLING_COMPRESSION,
            chatbot_id=chatbot_id,
            session_id=session_id,
            idempotency_key=f"rolling:{session_id}:{boundary_turn_index}",
            payload={"base_rolling": base_rolling},
        )
    )


def make_rolling_compression_handler(
    repository: SqlCompanionMemoryRepository,
    compress: CompressFn,
) -> JobHandler:
    """Build the B06 handler executing ``ROLLING_COMPRESSION`` jobs."""
    return lambda context: _run_compression(repository, compress, context)


def _run_compression(
    repository: SqlCompanionMemoryRepository,
    compress: CompressFn,
    context: JobContext,
) -> None:
    """Compress one session's turns; stale bases write nothing."""
    if context.session_id is None:
        raise ValueError("rolling compression job has no session_id")
    session_id = context.session_id
    fresh, base = _base_if_current(context)
    if not fresh:
        return
    turns = _completed_turns(repository, context.chatbot_id, session_id)
    if not turns:
        return
    result = compress(context, build_rolling_prompt(turns, base))
    _store_compressed(context.chatbot_id, session_id, base, result.content)


def _base_if_current(
    context: JobContext,
) -> tuple[bool, Optional[str]]:
    """Payload base when the session exists and still matches it."""
    assert context.session_id is not None  # guarded by _run_compression
    found, current = _read_rolling(context.chatbot_id, context.session_id)
    if not found:
        return False, None
    base = context.payload.get("base_rolling")
    return current == base, base


def _store_compressed(
    chatbot_id: ChatbotId,
    session_id: SessionId,
    base: Optional[str],
    raw: str,
) -> None:
    """Sanitize, fit, and base-guarded-store one rolling result."""
    content = fit_to_budget(
        sanitize_memory_text(raw),
        MAX_ROLLING_CHARS,
        MAX_ROLLING_TOKENS,
    )
    _store_rolling(chatbot_id, session_id, content, base)


def _completed_turns(
    repository: SqlCompanionMemoryRepository,
    chatbot_id: ChatbotId,
    session_id: SessionId,
) -> List[TurnRecord]:
    """One session's completed turns, oldest first."""
    turns = repository.get_recent_turns(
        chatbot_id, session_id, limit=_MAX_COMPRESS_TURNS
    )
    return [t for t in turns if is_completed_turn(t)]


def _read_rolling(
    chatbot_id: ChatbotId, session_id: SessionId
) -> tuple[bool, Optional[str]]:
    """Whether the session exists, plus its rolling summary (if any)."""
    with session_scope() as db:
        row = (
            db.query(CompanionSession)
            .filter_by(id=int(session_id), chatbot_id=int(chatbot_id))
            .one_or_none()
        )
        if row is None:
            return False, None
        return True, row.rolling_summary


def _store_rolling(
    chatbot_id: ChatbotId,
    session_id: SessionId,
    content: str,
    base: Optional[str],
) -> bool:
    """Replace the rolling summary only if its base still matches.

    False (writing nothing) when a concurrent compression already
    advanced past ``base``. Turn rows are never touched.
    """
    with session_scope() as db:
        query = _rolling_update(session_id, chatbot_id, base, content)
        result = db.execute(query)
        return result.rowcount == 1


def _rolling_update(
    session_id: SessionId,
    chatbot_id: ChatbotId,
    base: Optional[str],
    content: str,
) -> Update:
    """UPDATE for one session's summary, fenced on ``base``."""
    return (
        update(CompanionSession)
        .where(
            CompanionSession.id == int(session_id),
            CompanionSession.chatbot_id == int(chatbot_id),
            _base_matches(base),
        )
        .values(rolling_summary=content)
    )


def _base_matches(base: Optional[str]) -> ColumnElement[bool]:
    """Equality against the expected rolling base (None-safe)."""
    if base is None:
        return CompanionSession.rolling_summary.is_(None)
    return CompanionSession.rolling_summary == base


__all__ = [
    "CompressFn",
    "MAX_ROLLING_CHARS",
    "MAX_ROLLING_TOKENS",
    "RollingResult",
    "build_rolling_prompt",
    "make_rolling_compression_handler",
    "schedule_rolling_compression",
]
