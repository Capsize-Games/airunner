"""Service-owned companion session model (release issue B02)."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, Text

from airunner_services.database.base import BaseModel


class CompanionSession(BaseModel):
    """One companion conversation session: a bounded, inactivity-gap-
    rotated span of turns for one chatbot.

    Field names match upstream ``ChatSession`` (see
    ``release-planning/linux-v1/companion-contracts.md`` and W01 §3)
    minus ``user_id`` -- Desktop is single-user.
    """

    __tablename__ = "companion_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(
        Integer, ForeignKey("chatbots.id"), nullable=False, index=True
    )
    started_at = Column(DateTime, nullable=False)
    last_message_at = Column(DateTime, nullable=False, index=True)
    episodic_summary = Column(Text, nullable=True)
    rolling_summary = Column(Text, nullable=True)
    emotional_weight = Column(Float, nullable=True)
    key_topics = Column(JSON, nullable=True)
    summary_ready = Column(Boolean, default=False, nullable=False)


__all__ = ["CompanionSession"]
