"""Concrete ``CompanionMemoryRepository`` backed by Desktop's own
SQLAlchemy/SQLite database (release issues B02/B03).

B02 added session/turn persistence; B03 implements fact storage
(``get_facts``/``upsert_fact``) plus fact retraction/reopening and
the one-per-chatbot evolving narrative. Every method runs in exactly
one ``session_scope`` transaction and scopes every query by
``ChatbotId`` at the query level. No embedding columns or vector
index reads/writes live here: vector indexing is B04's scope, and
the pre-existing file/document knowledge tables are left untouched
until B14 migrates them.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, List, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from airunner_services.database.models.companion_fact import CompanionFact
from airunner_services.database.models.companion_narrative import (
    CompanionNarrative,
)
from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.models.companion_turn import CompanionTurn
from airunner_services.database.session import session_scope

from .contracts import ChatbotId, SessionId
from .memory_repository import FactRecord, SessionRecord, TurnRecord

# Bounded so a persistent concurrent-writer storm fails loudly (an
# unbounded retry loop would hang the caller) rather than looping
# forever; five is generous headroom over the number of writers this
# single-user desktop daemon plausibly runs at once.
_MAX_APPEND_TURN_ATTEMPTS = 5

# Upstream's characterized inactivity-gap rotation threshold (W01 §2): a
# session is reused if the gap since its last message is under this many
# hours, else a new one starts. Desktop has not chosen a different
# threshold (see memory_repository.py's get_or_start_session docstring),
# so this ports the upstream value as-is rather than inventing one.
DEFAULT_SESSION_GAP = timedelta(hours=4)


class StoredFactRecord(FactRecord):
    """A ``FactRecord`` with its stored provenance attached.

    A strict superset of the B01 contract: every extra field is
    optional, so a plain ``FactRecord`` still upserts (provenance
    fields default to unknown) and every stored fact reads back as
    this type (which *is* a ``FactRecord``, keeping ``get_facts``'
    return type honest). Subclassing -- rather than extending the
    B01 Protocol -- keeps this issue's scope additive: B01's
    contract and its regression file are untouched.

    ``event_id`` is the idempotency key: one extraction event
    produces at most one fact per chatbot, so redelivering the
    same event never duplicates it. ``retracted_at``/None is the
    active/retracted state; retraction never deletes the row.
    """

    subject: Optional[str] = None
    source: Optional[str] = None
    event_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    retracted_at: Optional[str] = None
    retraction_reason: Optional[str] = None


class NarrativeRecord(BaseModel):
    """One chatbot's evolving narrative memory (B03; B09 rewrites it).

    ``version`` counts rewrites starting at 1 for the first stored
    revision; a hand-constructed record carries 0, meaning "no
    stored narrative yet". Timestamps are ISO strings, matching
    ``SessionRecord``'s convention.
    """

    model_config = ConfigDict(extra="forbid")

    narrative_id: Optional[int] = None
    chatbot_id: ChatbotId
    content: str = ""
    version: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


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
            # Upstream rotates only when the gap *exceeds* the threshold
            # (pinned commit 8157628a..., llm/session_manager.py's
            # _detect_gap: "> SESSION_GAP_HOURS"), so a gap exactly equal
            # to the threshold still reuses the session. A strict "<"
            # here would rotate one instant early, diverging from the
            # characterized behavior at the boundary (release issue B02
            # second-review finding).
            if (
                latest is not None
                and (now - latest.last_message_at) <= self._session_gap
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
            existing = _find_existing_turn(db, turn)
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

            created_at = self._clock()

            # Concurrent writers can both pass the idempotency check
            # above (neither has committed yet) and both compute the
            # same next turn_index from a plain COUNT/MAX query -- that
            # count alone cannot serialize against a writer racing it
            # (release issue B02 second-review finding: "concurrent
            # turns receive duplicate indexes"). The unique
            # (session_id, turn_index) constraint on CompanionTurn is
            # the actual backstop: attempt the insert inside a
            # savepoint, and on a constraint violation, roll back just
            # that savepoint and retry with a freshly computed index
            # (or, if the loser turns out to be a genuine duplicate
            # completion that another writer just committed, return
            # that instead -- making concurrent duplicate delivery
            # idempotent rather than an uncaught IntegrityError).
            for _attempt in range(_MAX_APPEND_TURN_ATTEMPTS):
                next_index = (
                    db.query(func.coalesce(func.max(CompanionTurn.turn_index), -1))
                    .filter(CompanionTurn.session_id == int(turn.session_id))
                    .scalar()
                    + 1
                )
                turn_row = CompanionTurn(
                    chatbot_id=int(turn.chatbot_id),
                    session_id=int(turn.session_id),
                    role=turn.role,
                    content=turn.content,
                    turn_index=next_index,
                    call_chain_id=str(turn.call_chain_id),
                    created_at=created_at,
                )
                savepoint = db.begin_nested()
                db.add(turn_row)
                try:
                    db.flush()
                except IntegrityError:
                    savepoint.rollback()
                    winner = _find_existing_turn(db, turn)
                    if winner is not None:
                        # The concurrent writer committed this exact
                        # completion event first -- idempotent return.
                        return _turn_to_record(winner)
                    # Otherwise it was purely a turn_index collision
                    # with a *different* turn; retry with a fresh index.
                    continue
                else:
                    # Same transaction as the insert above (session_scope
                    # commits once, on exit): a completed turn and its
                    # session's activity timestamp are never observed
                    # out of sync.
                    session_row.last_message_at = created_at
                    db.flush()
                    return _turn_to_record(turn_row)

            raise RuntimeError(
                f"Could not persist turn for chatbot {turn.chatbot_id} "
                f"session {turn.session_id} after "
                f"{_MAX_APPEND_TURN_ATTEMPTS} attempts (persistent "
                "concurrent writers)"
            )

    def get_recent_turns(
        self, chatbot_id: ChatbotId, session_id: SessionId, *, limit: int
    ) -> List[TurnRecord]:
        if limit <= 0:
            return []
        with session_scope() as db:
            # Push ordering/limit into SQL rather than loading the whole
            # session transcript and slicing in Python: a long-running
            # session's full history should never be pulled into memory
            # just to serve a bounded "recent turns" request (release
            # issue B02 second-review finding). Fetch the most recent
            # `limit` rows newest-first, then reverse for the
            # documented oldest-first return order.
            rows = (
                db.query(CompanionTurn)
                .filter(
                    CompanionTurn.chatbot_id == int(chatbot_id),
                    CompanionTurn.session_id == int(session_id),
                )
                .order_by(CompanionTurn.turn_index.desc())
                .limit(limit)
                .all()
            )
            return [_turn_to_record(row) for row in reversed(rows)]

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
        self,
        chatbot_id: ChatbotId,
        *,
        limit: int,
        include_retracted: bool = False,
    ) -> List[FactRecord]:
        """Return one chatbot's facts, most recently updated first.

        Retracted facts are excluded unless ``include_retracted``
        is set: recall (B05) must not resurrect withdrawn facts by
        default, while retraction management still needs to see
        them. ``include_retracted`` is defaulted, so the B01
        ``(chatbot_id, *, limit)`` call shape is unchanged.
        """
        if limit <= 0:
            return []
        with session_scope() as db:
            query = db.query(CompanionFact).filter(
                CompanionFact.chatbot_id == int(chatbot_id)
            )
            if not include_retracted:
                query = query.filter(
                    CompanionFact.retracted_at.is_(None)
                )
            rows = (
                query.order_by(CompanionFact.updated_at.desc())
                .limit(limit)
                .all()
            )
            return [_fact_to_record(row) for row in rows]

    def upsert_fact(self, fact: FactRecord) -> FactRecord:
        """Insert a new fact or update the stored one, idempotently.

        Three paths, in order:

        1. ``fact_id`` set: update that row's content/provenance in
           place (``updated_at`` advances, ``created_at`` and the
           retraction state are preserved). The lookup is scoped by
           ``chatbot_id``: another chatbot's ID raises ``ValueError``
           rather than touching that row.
        2. ``event_id`` set and already stored for this chatbot:
           return the existing row unchanged, the same
           return-existing semantics ``append_turn`` uses for a
           repeated completion event -- one event produces one
           fact, and redelivery is not an update.
        3. Otherwise insert a new row.

        Accepts a plain B01 ``FactRecord`` (extra provenance then
        defaults to unknown) or a ``StoredFactRecord``. Concurrent
        inserts of the same event collapse onto the unique
        ``(chatbot_id, event_id)`` constraint: the loser rolls back
        its savepoint and returns the winner's row instead of
        raising.
        """
        event_id = getattr(fact, "event_id", None)
        with session_scope() as db:
            if fact.fact_id is not None:
                return self._update_fact(db, fact, int(fact.fact_id))
            if event_id is not None:
                existing = _find_existing_fact(
                    db, fact.chatbot_id, event_id
                )
                if existing is not None:
                    return _fact_to_record(existing)
            return self._insert_fact(db, fact, event_id)

    def _update_fact(
        self, db, fact: FactRecord, fact_id: int
    ) -> FactRecord:
        row = self._scoped_fact(db, fact.chatbot_id, fact_id)
        row.subject = getattr(fact, "subject", None)
        row.content = fact.content
        row.source = getattr(fact, "source", None)
        if fact.source_turn_id is not None:
            row.source_turn_id = int(fact.source_turn_id)
        row.confidence = fact.confidence
        row.fact_metadata = dict(fact.metadata)
        row.updated_at = self._clock()
        db.flush()
        return _fact_to_record(row)

    def _insert_fact(
        self, db, fact: FactRecord, event_id: Optional[str]
    ) -> FactRecord:
        now = self._clock()
        row = CompanionFact(
            chatbot_id=int(fact.chatbot_id),
            subject=getattr(fact, "subject", None),
            content=fact.content,
            source=getattr(fact, "source", None),
            source_turn_id=(
                int(fact.source_turn_id)
                if fact.source_turn_id is not None
                else None
            ),
            event_id=event_id,
            confidence=fact.confidence,
            fact_metadata=dict(fact.metadata),
            created_at=now,
            updated_at=now,
        )
        savepoint = db.begin_nested()
        db.add(row)
        try:
            db.flush()
        except IntegrityError:
            # A concurrent writer committed this exact event first.
            savepoint.rollback()
            winner = (
                _find_existing_fact(db, fact.chatbot_id, event_id)
                if event_id is not None
                else None
            )
            if winner is not None:
                return _fact_to_record(winner)
            raise
        return _fact_to_record(row)

    def retract_fact(
        self,
        chatbot_id: ChatbotId,
        fact_id: int,
        *,
        reason: Optional[str] = None,
    ) -> FactRecord:
        """Mark one fact retracted without deleting its row.

        The fact keeps its content and provenance and stays
        readable via ``include_retracted=True``; ``reopen_fact``
        reverses this. Scoped by chatbot: another chatbot's fact
        ID raises ``ValueError``.
        """
        with session_scope() as db:
            row = self._scoped_fact(db, chatbot_id, fact_id)
            row.retracted_at = self._clock()
            row.retraction_reason = reason
            db.flush()
            return _fact_to_record(row)

    def reopen_fact(
        self, chatbot_id: ChatbotId, fact_id: int
    ) -> FactRecord:
        """Clear one fact's retraction, restoring it to recall."""
        with session_scope() as db:
            row = self._scoped_fact(db, chatbot_id, fact_id)
            row.retracted_at = None
            row.retraction_reason = None
            row.updated_at = self._clock()
            db.flush()
            return _fact_to_record(row)

    def _scoped_fact(
        self, db, chatbot_id: ChatbotId, fact_id: int
    ) -> CompanionFact:
        row = (
            db.query(CompanionFact)
            .filter(
                CompanionFact.id == int(fact_id),
                CompanionFact.chatbot_id == int(chatbot_id),
            )
            .one_or_none()
        )
        if row is None:
            raise ValueError(
                f"No fact {fact_id} for chatbot {chatbot_id}"
            )
        return row

    def get_narrative(
        self, chatbot_id: ChatbotId
    ) -> Optional[NarrativeRecord]:
        """Return one chatbot's narrative, or None if never written."""
        with session_scope() as db:
            row = (
                db.query(CompanionNarrative)
                .filter(
                    CompanionNarrative.chatbot_id == int(chatbot_id)
                )
                .one_or_none()
            )
            if row is None:
                return None
            return _narrative_to_record(row)

    def update_narrative(
        self, chatbot_id: ChatbotId, content: str
    ) -> NarrativeRecord:
        """Replace one chatbot's narrative, creating it at version 1
        or bumping ``version`` on each rewrite. A concurrent
        first-write collapses onto the unique ``chatbot_id``
        constraint: the loser re-reads the winner's row and applies
        its update on top instead of raising."""
        now = self._clock()
        with session_scope() as db:
            row = (
                db.query(CompanionNarrative)
                .filter(
                    CompanionNarrative.chatbot_id == int(chatbot_id)
                )
                .one_or_none()
            )
            if row is None:
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
                    row = (
                        db.query(CompanionNarrative)
                        .filter(
                            CompanionNarrative.chatbot_id
                            == int(chatbot_id)
                        )
                        .one()
                    )
                    row.content = content
                    row.version += 1
                    row.updated_at = now
                    db.flush()
            else:
                row.content = content
                row.version += 1
                row.updated_at = now
                db.flush()
            return _narrative_to_record(row)


def _find_existing_turn(db, turn: TurnRecord) -> Optional[CompanionTurn]:
    """Return the already-persisted row for this exact completion event,
    if any -- the shared lookup behind both the fast-path idempotency
    check and the post-conflict "who won the race" check in
    ``append_turn``."""
    return (
        db.query(CompanionTurn)
        .filter(
            CompanionTurn.chatbot_id == int(turn.chatbot_id),
            CompanionTurn.call_chain_id == str(turn.call_chain_id),
            CompanionTurn.role == turn.role,
        )
        .one_or_none()
    )


def _find_existing_fact(
    db, chatbot_id: ChatbotId, event_id: str
) -> Optional[CompanionFact]:
    """Return the already-persisted row for this exact extraction
    event, if any -- the shared lookup behind both the fast-path
    idempotency check and the post-conflict "who won the race"
    check in ``upsert_fact``."""
    return (
        db.query(CompanionFact)
        .filter(
            CompanionFact.chatbot_id == int(chatbot_id),
            CompanionFact.event_id == event_id,
        )
        .one_or_none()
    )


def _fact_to_record(row: CompanionFact) -> StoredFactRecord:
    return StoredFactRecord(
        fact_id=row.id,
        chatbot_id=row.chatbot_id,
        content=row.content,
        source_turn_id=row.source_turn_id,
        confidence=row.confidence,
        metadata=dict(row.fact_metadata or {}),
        subject=row.subject,
        source=row.source,
        event_id=row.event_id,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        retracted_at=(
            row.retracted_at.isoformat()
            if row.retracted_at is not None
            else None
        ),
        retraction_reason=row.retraction_reason,
    )


def _narrative_to_record(row: CompanionNarrative) -> NarrativeRecord:
    return NarrativeRecord(
        narrative_id=row.id,
        chatbot_id=row.chatbot_id,
        content=row.content,
        version=row.version,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
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


__all__ = [
    "DEFAULT_SESSION_GAP",
    "NarrativeRecord",
    "SqlCompanionMemoryRepository",
    "StoredFactRecord",
]
