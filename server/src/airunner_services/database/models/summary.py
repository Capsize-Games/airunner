"""Service-owned conversation summary model."""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from airunner_services.database.base import BaseModel


class Summary(BaseModel):
    """Persisted conversation summary entry."""

    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String, nullable=False, default="")
    timestamp = Column(
        DateTime,
        default=datetime.datetime.now(datetime.timezone.utc),
    )
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    conversation = relationship("Conversation", back_populates="summaries")


__all__ = ["Summary"]
