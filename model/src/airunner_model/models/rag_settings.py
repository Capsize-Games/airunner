"""Service-owned RAG settings model."""

from sqlalchemy import Column, Integer, String

from airunner_model.contract_enums import ModelService
from airunner_model.base import BaseModel


class RAGSettings(BaseModel):
    """Persist retrieval-augmented generation settings."""

    __tablename__ = "rag_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_service = Column(String, default=ModelService.LOCAL.value)
    model_path = Column(String, default="")
    chunk_size = Column(Integer, default=512)
    chunk_overlap = Column(Integer, default=50)


__all__ = ["RAGSettings"]