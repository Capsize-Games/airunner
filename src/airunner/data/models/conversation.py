import datetime
from sqlalchemy import Column, Integer, DateTime, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from airunner.data.models.base import BaseModel
from airunner.data.models.summary import Summary


class Conversation(BaseModel):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    title = Column(String, nullable=True)
    bot_mood = Column(Text, default="")
    key = Column(String, nullable=True)
    value = Column(JSON, nullable=False, default={})
    chatbot_id = Column(Integer, ForeignKey('chatbots.id'))
    chatbot_name = Column(String, nullable=False, default="")
    user_id = Column(Integer, ForeignKey('users.id'))
    user_name = Column(String, nullable=False, default="")
    status = Column(String, nullable=True, default="")
    last_updated_message_id = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    user_data = Column(JSON, nullable=True)


Conversation.summaries = relationship(
    "Summary", 
    order_by=Summary.id, 
    back_populates="conversation"
)