from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel


class SavedPrompt(BaseModel):
    __tablename__ = "saved_prompts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(String, nullable=True)
    secondary_prompt = Column(String, nullable=True)
    negative_prompt = Column(String, nullable=True)
    secondary_negative_prompt = Column(String, nullable=True)
