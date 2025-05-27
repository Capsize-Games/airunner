from typing import Optional
import logging
import datetime
import uuid
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    String,
    Text,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship, joinedload

from airunner.data.models.base import BaseModel
from airunner.data.models.summary import Summary
from airunner.data.models.chatbot import Chatbot
from airunner.data.models.user import User

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer


class Conversation(BaseModel):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    title = Column(String, nullable=True)
    bot_mood = Column(Text, default="")
    key = Column(String, nullable=True)
    value = Column(JSON, nullable=False, default={})
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"))
    chatbot_name = Column(String, nullable=False, default="")
    user_id = Column(Integer, ForeignKey("users.id"))
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
    def create(cls, chatbot: Optional[Chatbot] = None, user: Optional[User] = None):
        previous_conversation = (
            cls.objects.options(joinedload(cls.summaries))
            .order_by(cls.id.desc())
            .first()
        )

        # Ensure a valid chatbot exists
        if not chatbot:
            chatbot = None
            try:
                if previous_conversation:
                    chatbot = Chatbot.objects.get(previous_conversation.chatbot_id)
            except Exception:
                chatbot = None
            if not chatbot:
                try:
                    chatbot = Chatbot.objects.first()
                except Exception:
                    chatbot = None
            if not chatbot:
                try:
                    unique_name = f"DefaultChatbot_{uuid.uuid4()}"
                    chatbot = Chatbot.objects.create(
                        name=unique_name, botname="Computer"
                    )
                except Exception:
                    # As a last resort, create a minimal in-memory Chatbot
                    chatbot = Chatbot(name="Fallback", botname="Computer")
            chatbot_id = chatbot.id
            chatbot_botname = chatbot.botname
        else:
            chatbot_id = chatbot.id
            chatbot_botname = chatbot.botname

        # Ensure a valid user exists
        if not user:
            if previous_conversation:
                user = User.objects.get(previous_conversation.user_id)
            if not user:
                user = User.objects.first()
            if not user:
                user_dc = User.objects.create(username="User")
                from airunner.data.session_manager import session_scope

                with session_scope() as session:
                    orm_user = session.query(User).filter_by(id=user_dc.id).first()
                    user_id = orm_user.id
                    user_username = orm_user.username
            else:
                user_id = user.id
                user_username = user.username
        else:
            user_id = user.id
            user_username = user.username

        conversation = cls(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            title="",
            key="",
            value=[],  # Always use empty list, not None
            chatbot_id=chatbot_id,
            user_id=user_id,
            chatbot_name=chatbot_botname,
            user_name=user_username,
            bot_mood=(
                previous_conversation.bot_mood if previous_conversation else None
            ),
        )
        conversation.save()
        conversation = (
            cls.objects.options(joinedload(cls.summaries))
            .order_by(cls.id.desc())
            .first()
        )
        # Always return a dataclass, not ORM object
        return conversation.to_dataclass() if conversation else None

    @classmethod
    def most_recent(cls) -> Optional["Conversation"]:
        try:
            conversation = cls.objects.order_by(cls.id.desc()).first()

            if conversation:
                return Conversation(**conversation.to_dict())
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in most_recent(): {e}")


Conversation.summaries = relationship(
    "Summary", order_by=Summary.id, back_populates="conversation"
)
