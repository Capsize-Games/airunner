from sqlalchemy import Column, Integer, Boolean, String, BigInteger, ForeignKey

from airunner.data.models.base import BaseModel
from airunner.enums import ModelService


class RAGSettings(BaseModel):
    __tablename__ = "rag_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, default=False)
    model_service = Column(String, default=ModelService.LOCAL.value)
    model_path = Column(String, default="")
