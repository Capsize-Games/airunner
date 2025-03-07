from sqlalchemy import Column, Integer, String, Boolean

from airunner.data.models.base import BaseModel


class Lora(BaseModel):
    __tablename__ = 'lora'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="")
    scale = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=False)
    loaded = Column(Boolean, nullable=False, default=False)
    trigger_word = Column(String, nullable=True)
    path = Column(String, nullable=True)
    version = Column(String, nullable=True)
