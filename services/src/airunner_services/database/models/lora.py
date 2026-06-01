"""Stub — LoRA table was dropped by migration 0f8b4e43d1c2."""

from airunner_services.database.base import BaseModel
from sqlalchemy import Column, Integer, String


class Lora(BaseModel):
    __tablename__ = "lora"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    path = Column(String, default="")


__all__ = ["Lora"]
