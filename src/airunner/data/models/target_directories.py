from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from airunner.data.models.base import BaseModel


class TargetDirectories(BaseModel):
    __tablename__ = 'target_directories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(Integer, ForeignKey('chatbots.id'))
    directory_path = Column(String)

    chatbot = relationship("Chatbot", back_populates="target_directories")
