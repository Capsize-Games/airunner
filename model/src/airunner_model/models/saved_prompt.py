"""Service-owned saved prompt model."""

from sqlalchemy import Column, Integer, String

from airunner_model.base import BaseModel


class SavedPrompt(BaseModel):
    """Persist reusable prompt combinations for art generation."""

    __tablename__ = "saved_prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(String, nullable=True)
    secondary_prompt = Column(String, nullable=True)
    negative_prompt = Column(String, nullable=True)
    secondary_negative_prompt = Column(String, nullable=True)


__all__ = ["SavedPrompt"]