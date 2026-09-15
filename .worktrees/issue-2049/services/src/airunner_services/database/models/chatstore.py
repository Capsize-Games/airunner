"""Service-owned chatstore model."""

import datetime

from sqlalchemy import Column, Integer, JSON, String

from airunner_services.database.base import BaseModel


class Chatstore(BaseModel):
    """Persist arbitrary chatbot key/value state."""

    __tablename__ = "chatstore"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_created = Column(
        String,
        default=datetime.datetime.now().isoformat(),
    )
    key = Column(String, nullable=False, default="")
    value = Column(JSON, nullable=False, default={})


__all__ = ["Chatstore"]