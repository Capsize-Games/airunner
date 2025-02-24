from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from airunner.data.models.base import Base


class TargetFiles(Base):
    __tablename__ = 'target_files'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(Integer, ForeignKey('chatbots.id'))
    file_path = Column(String)

    chatbot = relationship("Chatbot", back_populates="target_files")