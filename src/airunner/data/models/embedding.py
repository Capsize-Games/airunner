from sqlalchemy import Column, Integer, String, Boolean

from airunner.data.models.base import Base


class Embedding(Base):
    __tablename__ = "embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    version = Column(String, nullable=False)
    tags = Column(String, default="")
    active = Column(Boolean, default=False)
    trigger_word = Column(String, default="")