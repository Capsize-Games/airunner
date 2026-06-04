"""Service-owned canvas document model for Konva JSON persistence."""

from sqlalchemy import Column, Integer, Text

from airunner_services.database.base import BaseModel


class CanvasDocument(BaseModel):
    """Persist the serialized Konva canvas document as a JSON blob."""

    __tablename__ = "canvas_document"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document = Column(Text, nullable=True)


__all__ = ["CanvasDocument"]
