"""Stub — FineTunedModel table was dropped by migration 0f8b4e43d1c2."""

from airunner.base import BaseModel
from sqlalchemy import Column, Integer, String


class FineTunedModel(BaseModel):
    __tablename__ = "fine_tuned_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    path = Column(String, default="")


__all__ = ["FineTunedModel"]
