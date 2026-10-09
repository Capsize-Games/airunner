"""Service-owned companion fact model (release issue B03)."""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from airunner_services.database.base import BaseModel


class CompanionFact(BaseModel):
    """One structured, chatbot-scoped memory fact.

    ``subject``/``source``/``source_turn_id`` plus the timestamp
    columns are the fact's provenance: where it came from and when.
    ``retracted_at``/``retraction_reason`` implement retraction as a
    state change, never a row deletion, so a retracted fact keeps its
    full history and can be reopened (release issue B03 acceptance
    criterion). No embedding column lives here: vector indexing is
    explicitly out of B03's scope (B04 owns the embeddings index),
    and the pre-existing file/document knowledge tables are left
    untouched until B14 migrates them.

    The unique constraint on ``(chatbot_id, event_id)`` is what
    makes fact ingestion idempotent: redelivering the same
    extraction event returns the existing row instead of inserting
    a duplicate, while the same event ID from a *different*
    chatbot still inserts -- chatbot isolation by construction.
    ``event_id`` is nullable for facts with no extraction event
    (SQLite treats NULLs as distinct in unique constraints, so
    those rows never collide with each other).
    """

    __tablename__ = "companion_facts"
    __table_args__ = (
        UniqueConstraint(
            "chatbot_id",
            "event_id",
            name="uq_companion_facts_chatbot_event",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(
        Integer, ForeignKey("chatbots.id"), nullable=False, index=True
    )
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    source_turn_id = Column(
        Integer,
        ForeignKey("companion_turns.id"),
        nullable=True,
        index=True,
    )
    event_id = Column(String, nullable=True, index=True)
    confidence = Column(Float, nullable=False, default=1.0)
    fact_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    retracted_at = Column(DateTime, nullable=True)
    retraction_reason = Column(String, nullable=True)


__all__ = ["CompanionFact"]
