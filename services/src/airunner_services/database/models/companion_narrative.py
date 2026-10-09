"""Service-owned companion narrative model (release issue B03)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text

from airunner_services.database.base import BaseModel


class CompanionNarrative(BaseModel):
    """One chatbot's evolving narrative memory: a single rolling
    text, rewritten in place by each update.

    Exactly one row per chatbot (unique ``chatbot_id``): there is
    no per-session or per-turn narrative history table -- B09's
    rolling compression rewrites this row, and ``version`` counts
    those rewrites so a caller can tell a fresh narrative from a
    long-evolved one. ``created_at``/``updated_at`` are the rest
    of its provenance. No embedding column: vector indexing is
    B04's scope, not this issue's.
    """

    __tablename__ = "companion_narratives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(
        Integer,
        ForeignKey("chatbots.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    content = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


__all__ = ["CompanionNarrative"]
