from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from airunner.components.data.models.base import BaseModel


class Document(BaseModel):
    """Document model for unified RAG collection with cache integrity tracking."""

    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False, unique=True)
    active = Column(Boolean, default=True)
    indexed = Column(Boolean, default=False)
    index_uuid = Column(String, nullable=True, unique=True)
    file_hash = Column(String, nullable=True)
    indexed_at = Column(DateTime, nullable=True)
    file_size = Column(Integer, nullable=True)
