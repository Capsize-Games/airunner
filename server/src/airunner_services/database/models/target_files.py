"""Service-owned target-file model."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from airunner_services.database.base import BaseModel


class TargetFiles(BaseModel):
    """Persist chatbot-linked file targets for retrieval workflows."""

    __tablename__ = "target_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"))
    file_path = Column(String)

    chatbot = relationship("Chatbot", back_populates="target_files")


__all__ = ["TargetFiles"]
