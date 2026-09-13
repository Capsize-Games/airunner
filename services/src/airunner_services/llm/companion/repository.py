"""Concrete ``CompanionMemoryRepository`` backed by Desktop's own
SQLAlchemy/SQLite database (release issue B02).

Implements session/turn persistence only. Fact storage
(``get_facts``/``upsert_fact``) is B03's scope (see
``release-planning/linux-v1/companion-contracts.md``): ``get_facts``
returns an empty list, an honest answer since no fact storage exists
yet to read from, and ``upsert_fact`` raises ``NotImplementedError``
rather than silently no-op-ing, so a caller cannot mistake "not yet
implemented" for "saved".
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, List

from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.models.companion_turn import CompanionTurn
from airunner_services.database.session import session_scope

from .contracts import ChatbotId, SessionId
from .memory_repository import FactRecord, SessionRecord, TurnRecord

# Upstream's characterized inactivity-gap rotation threshold (W01 §2): a
# session is reused if the gap since its last message is under this many
# hours, else a new one starts. Desktop has not chosen a different
# threshold (see memory_repository.py's get_or_start_session docstring),
# so this ports the upstream value as-is rather than inventing one.
DEFAULT_SESSION_GAP = timedelta(hours=4)


class SqlCompanionMemoryRepository:
    """SQLAlchemy-backed ``CompanionMemoryRepository``.

    Every method is scoped by ``ChatbotId`` (and, for turns,
    ``SessionId``) at the query level -- not by convention -- matching
    the Protocol's own stated requirement that one chatbot's memory can
    never be read or written by another by construction.
    """

    def __init__(
        self,
        *,
        session_gap: timedelta = DEFAULT_SESSION_GAP,
        clock: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self._session_gap = session_gap
        self._clock = clock

    def get_or_start_session(self, chatbot_id: ChatbotId) -> SessionRecord:
        now = self._clock()
        with session_scope() as db:
            latest = (
                db.query(CompanionSession)
                .filter(CompanionSession.chatbot_id == int(chatbot_id))
                .order_by(CompanionSession.last_message_at.desc())
                .first()
            )
            if (
                latest is not None
                and (now - latest.last_message_at) < self._session_gap
            ):
                return _session_to_record(latest)

            session_row = CompanionSession(
                chatbot_id=int(chatbot_id),
                started_at=now,
                last_message_at=now,
                summary_ready=False,
            )
            db.add(session_row)
            db.flush()
            return _session_to_record(session_row)

    def append_turn(self, turn: TurnRecord) -> TurnRecord:
        with session_scope() as db:
            existing = (
                db.query(CompanionTurn)
                .filter(
                    CompanionTurn.chatbot_id == int(turn.chatbot_id),
                    CompanionTurn.call_chain_id == str(turn.call_chain_id),
                    CompanionTurn.role == turn.role,
                )
                .one_or_none()
            )
            if existing is not None:
                # Idempotent: this exact (chatbot, call_chain_id, role)
                # completion was already recorded -- return the existing
                # row instead of inserting a duplicate (release issue
                # B02 acceptance criterion).
                return _turn_to_record(existing)

            session_row = (
                db.query(CompanionSession)
                .filter(
                    CompanionSession.id == int(turn.session_id),
                    CompanionSession.chatbot_id == int(turn.chatbot_id),
                )
                .one_or_none()
            )
            if session_row is None:
                raise ValueError(
                    f"No session {turn.session_id} for chatbot "
                    f"{turn.chatbot_id}"
                )

            next_index = (
                db.query(CompanionTurn)
                .filter(
                    CompanionTurn.chatbot_id == int(turn.chatbot_id),
                    CompanionTurn.session_id == int(turn.session_id),
                )
                .count()
            )
            created_at = self._clock()
            turn_row = CompanionTurn(
                chatbot_id=int(turn.chatbot_id),
                session_id=int(turn.session_id),
                role=turn.role,
                content=turn.content,
                turn_index=next_index,
                call_chain_id=str(turn.call_chain_id),
                created_at=created_at,
            )
            db.add(turn_row)
            # Same transaction as the insert above (session_scope commits
            # once, on exit): a completed turn and its session's activity
            # timestamp are never observed out of sync.
            session_row.last_message_at = created_at
            db.flush()
            return _turn_to_record(turn_row)

    def get_recent_turns(
        self, chatbot_id: ChatbotId, session_id: SessionId, *, limit: int
    ) -> List[TurnRecord]:
        with session_scope() as db:
            rows = (
                db.query(CompanionTurn)
                .filter(
                    CompanionTurn.chatbot_id == int(chatbot_id),
                    CompanionTurn.session_id == int(session_id),
                )
                .order_by(CompanionTurn.turn_index.asc())
                .all()
            )
            trimmed = rows[-limit:] if limit > 0 else []
            return [_turn_to_record(row) for row in trimmed]

    def update_session_summary(self, session: SessionRecord) -> None:
        with session_scope() as db:
            session_row = (
                db.query(CompanionSession)
                .filter(
                    CompanionSession.id == int(session.session_id),
                    CompanionSession.chatbot_id == int(session.chatbot_id),
                )
                .one_or_none()
            )
            if session_row is None:
                raise ValueError(
                    f"No session {session.session_id} for chatbot "
                    f"{session.chatbot_id}"
                )
            session_row.episodic_summary = session.episodic_summary
            session_row.rolling_summary = session.rolling_summary
            session_row.emotional_weight = session.emotional_weight
            session_row.key_topics = list(session.key_topics)
            session_row.summary_ready = session.summary_ready

    def get_facts(
        self, chatbot_id: ChatbotId, *, limit: int
    ) -> List[FactRecord]:
        del chatbot_id, limit
        return []

    def upsert_fact(self, fact: FactRecord) -> FactRecord:
        del fact
        raise NotImplementedError(
            "Fact storage is not implemented yet -- see release issue B03 "
            "(CompanionMemoryRepository.upsert_fact)."
        )


def _session_to_record(row: CompanionSession) -> SessionRecord:
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


def _turn_to_record(row: CompanionTurn) -> TurnRecord:
    return TurnRecord(
        turn_id=row.id,
        chatbot_id=row.chatbot_id,
        session_id=row.session_id,
        role=row.role,
        content=row.content,
        turn_index=row.turn_index,
        call_chain_id=row.call_chain_id,
    )


__all__ = ["DEFAULT_SESSION_GAP", "SqlCompanionMemoryRepository"]
