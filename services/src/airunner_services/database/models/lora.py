"""Service-owned LoRA model with trigger word support."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from airunner_services.database.base import BaseModel


class Lora(BaseModel):
    """Persist LoRA model metadata including trigger words."""

    __tablename__ = "lora"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    path = Column(String, default="")
    enabled = Column(Boolean, default=False)
    trigger_words = Column(Text, default="")  # comma-separated


__all__ = ["Lora"]
