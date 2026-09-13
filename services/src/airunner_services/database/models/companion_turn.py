"""Service-owned companion turn model (release issue B02)."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from airunner_services.database.base import BaseModel


class CompanionTurn(BaseModel):
    """One persisted companion conversation turn.

    Field names match upstream ``ConversationTurn`` (see
    ``release-planning/linux-v1/companion-contracts.md`` and W01 §3)
    minus ``embedding_enc`` (B04 owns embeddings) and
    ``conversation_id`` (an open question, not an erased assumption --
    see companion-contracts.md §4).

    The unique constraint on ``(chatbot_id, call_chain_id, role)`` is
    what makes ``append_turn`` idempotent: one ``call_chain_id``
    represents one full request/turn round trip and produces at most
    one row per role (the user's turn and the assistant's reply share
    the same ``call_chain_id``, so ``role`` must be part of the key --
    release issue B02's "repeated completion event is idempotent"
    acceptance criterion).

    The unique constraint on ``(session_id, turn_index)`` is the
    database-level backstop against the turn-index race under
    concurrent writers: two concurrent completions for the same
    session must never both compute and commit the same index (release
    issue B02 second-review finding). ``append_turn`` catches the
    resulting ``IntegrityError`` and retries with a freshly computed
    index rather than relying on an application-level count alone,
    which cannot serialize against a concurrent writer by itself.
    """

    __tablename__ = "companion_turns"
    __table_args__ = (
        UniqueConstraint(
            "chatbot_id",
            "call_chain_id",
            "role",
            name="uq_companion_turns_chatbot_call_chain_role",
        ),
        UniqueConstraint(
            "session_id",
            "turn_index",
            name="uq_companion_turns_session_turn_index",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(
        Integer, ForeignKey("chatbots.id"), nullable=False, index=True
    )
    session_id = Column(
        Integer,
        ForeignKey("companion_sessions.id"),
        nullable=False,
        index=True,
    )
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    turn_index = Column(Integer, nullable=False)
    call_chain_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)


__all__ = ["CompanionTurn"]
