"""Embedding model with trigger word and enabled support."""

from airunner_services.database.base import BaseModel
from sqlalchemy import Boolean, Column, Integer, String, Text


class Embedding(BaseModel):
    """Persist textual inversion embedding metadata."""

    __tablename__ = "embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    path = Column(String, default="")
    enabled = Column(Boolean, default=False)
    trigger_words = Column(Text, default="")  # comma-separated


__all__ = ["Embedding"]
