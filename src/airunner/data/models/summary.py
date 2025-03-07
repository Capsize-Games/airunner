import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship

from airunner.data.models.base import BaseModel


class Summary(BaseModel):
    __tablename__ = 'summaries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String, nullable=False, default="")
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    conversation = relationship("Conversation", back_populates="summaries")
