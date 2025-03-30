from typing import Optional
import logging
import datetime
from sqlalchemy import Column, Integer, DateTime, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship, joinedload

from airunner.data.models.base import BaseModel
from airunner.data.models.summary import Summary
from airunner.data.models.chatbot import Chatbot
from airunner.data.models.user import User

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer


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
    last_analysis_time = Column(DateTime, nullable=True)
    last_analyzed_message_id = Column(Integer, nullable=True)

    @property
    def formatted_messages(self) -> str:
        messages = self.value
        if messages:
            context = ""
            for message in messages:
                context += f"{message['role']}: {message['blocks'][0]['text']}\n"
            return context
        return ""

    def summarize(self) -> str:
        messages = self.formatted_messages
        if messages != "":
            parser = PlaintextParser.from_string(messages, Tokenizer("english"))
            summarizer = LexRankSummarizer()
            sentence_count = 1
            summary = summarizer(parser.document, sentence_count)
            summary_string = "\n".join([str(sentence) for sentence in summary])
            
            return summary_string
        return ""

    @classmethod
    def delete(cls, pk=None, **kwargs):
        Summary.objects.delete(conversation_id=pk)
        cls.objects.delete(pk, **kwargs)

    @classmethod
    def create(
        cls, 
        chatbot: Optional[Chatbot] = None, 
        user: Optional[User] = None
    ):
        previous_conversation = cls.objects.options(
            joinedload(cls.summaries)
        ).order_by(
            cls.id.desc()
        ).first()
        
        if not chatbot:
            if previous_conversation:
                chatbot = Chatbot.objects.get(previous_conversation.chatbot_id)
            else:
                chatbot = Chatbot.objects.first()

        if not user:
            if previous_conversation:
                user = User.objects.get(previous_conversation.user_id)
            else:
                user = User.objects.first()
            if not user:
                user = User.objects.create(username="User")
                user = User.objects.first()

        conversation = cls(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            title="",
            key="",
            value=None,
            chatbot_id=chatbot.id,
            user_id=user.id,
            chatbot_name=chatbot.name,
            user_name=user.username,
            bot_mood=previous_conversation.bot_mood if previous_conversation else None
        )
        conversation.save()
        conversation = cls.objects.options(
            joinedload(cls.summaries)
        ).order_by(
            cls.id.desc()
        ).first()
        return conversation

    @classmethod
    def most_recent(cls) -> Optional['Conversation']:
        try:
            conversation = cls.objects.order_by(
                cls.id.desc()
            ).first()
            
            if conversation:
                return Conversation(**conversation.to_dict())
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in most_recent(): {e}")


Conversation.summaries = relationship(
    "Summary", 
    order_by=Summary.id, 
    back_populates="conversation"
)
