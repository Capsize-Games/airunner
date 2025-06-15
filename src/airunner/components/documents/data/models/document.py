from sqlalchemy import Column, Integer, String, Boolean

from airunner.components.data.models.base import BaseModel


class Document(BaseModel):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False, unique=True)
    active = Column(Boolean, default=True)
    indexed = Column(Boolean, default=False)
    index_uuid = Column(String, nullable=True, unique=True)
