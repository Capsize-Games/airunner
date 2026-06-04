"""Service-owned LoRA model with trigger word and weight support."""

from sqlalchemy import Boolean, Column, Float, Integer, String, Text

from airunner_services.database.base import BaseModel


class Lora(BaseModel):
    """Persist LoRA model metadata including trigger words and weight."""

    __tablename__ = "lora"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="")
    path = Column(String, default="")
    enabled = Column(Boolean, default=False)
    trigger_words = Column(Text, default="")  # comma-separated
    weight = Column(Float, default=1.0)


__all__ = ["Lora"]
