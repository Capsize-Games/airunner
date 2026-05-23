"""Service-owned target-directory model."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from airunner_model.base import BaseModel


class TargetDirectories(BaseModel):
    """Persist chatbot-linked directory targets for retrieval workflows."""

    __tablename__ = "target_directories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"))
    directory_path = Column(String)

    chatbot = relationship(
        "Chatbot",
        back_populates="target_directories",
    )


__all__ = ["TargetDirectories"]