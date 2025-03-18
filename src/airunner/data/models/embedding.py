from sqlalchemy import Column, Integer, String, Boolean

from airunner.data.models.base import BaseModel


class Embedding(BaseModel):
    __tablename__ = "embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="")
    path = Column(String, nullable=False, default="")
    version = Column(String, nullable=False, default="")
    tags = Column(String, default="")
    active = Column(Boolean, default=False)
    trigger_word = Column(String, default="")
