from sqlalchemy import Column, Integer, String
from airunner.components.data.models.base import BaseModel


class ZimFile(BaseModel):
    """Persistent model for local ZIM files."""

    __tablename__ = "zimfiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    title = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    updated = Column(String, nullable=True)
    size = Column(Integer, nullable=True)
