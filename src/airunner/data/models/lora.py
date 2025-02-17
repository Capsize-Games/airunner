from sqlalchemy import Column, Integer, String, Boolean

from airunner.data.models.base import Base


class Lora(Base):
    __tablename__ = 'lora'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    scale = Column(Integer, nullable=False)
    enabled = Column(Boolean, nullable=False)
    loaded = Column(Boolean, default=False, nullable=False)
    trigger_word = Column(String, nullable=True)
    path = Column(String, nullable=True)
    version = Column(String, nullable=True)
