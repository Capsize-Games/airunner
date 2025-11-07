from typing import Optional
import datetime
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    DateTime,
    String,
    Text,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship, joinedload

from airunner.components.data.models.base import BaseModel
from airunner.components.llm.data.summary import Summary
from airunner.components.llm.data.chatbot import Chatbot
from airunner.components.user.data.user import User

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application.get_logger import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

class Conversation(BaseModel):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc)
    )
    title = Column(String, nullable=True)
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
    current = Column(Boolean, default=False)

    @property
    def formatted_messages(self) -> str:
        messages = self.value
        if messages:
            context = ""
            for message in messages:
                # Prefer bot_mood for bot, user_mood for user if present
                mood_info = ""
                if message.get("is_bot"):
                    mood = message.get("bot_mood")
                    if mood:
                        mood_info = f" [mood: {mood}]"
                else:
                    user_mood = message.get("user_mood")
                    if user_mood:
                        mood_info = f" [user mood: {user_mood}]"
                name = message.get("name", "Unknown")
                content = message.get("content", "")
                context += f"{name}: {content}{mood_info}\n"
            return context
        return ""

    def summarize(self) -> str:
        messages = self.formatted_messages
        if messages != "":
            parser = PlaintextParser.from_string(
                messages, Tokenizer("english")
            )
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
        cls, chatbot: Optional[Chatbot] = None, user: Optional[User] = None
    ):
        previous_conversation = (
            cls.objects.options(joinedload(cls.summaries))
            .order_by(cls.id.desc())
            .first()
        )

        # Ensure a valid chatbot exists
        chatbot_id = None
        chatbot_botname = None
        if not chatbot:
            chatbot = None
            # Only try to get if previous_conversation and chatbot_id are valid (not None)
            prev_chatbot_id = (
                getattr(previous_conversation, "chatbot_id", None)
                if previous_conversation
                else None
            )
            if prev_chatbot_id is not None:
                try:
                    chatbot = Chatbot.objects.get(prev_chatbot_id)
                except Exception as e:
                    logger.error(
                        f"Error retrieving chatbot from previous conversation: {e}"
                    )
                    chatbot = None
            if not chatbot:
                try:
                    chatbot = Chatbot.objects.first()
                except Exception as e:
                    logger.error(
                        f"Error retrieving first chatbot: {e}"
                    )
                    chatbot = None
            if not chatbot:
                try:
                    unique_name = f"DefaultChatbot_{uuid.uuid4()}"
                    chatbot = Chatbot.objects.create(
                        name=unique_name, botname="Computer"
                    )
                    Chatbot.make_current(chatbot.id)
                except Exception as e:
                    logger.error(
                        f"Error creating default chatbot: {e}"
                    )
                    chatbot = None
            if not chatbot:
                logger.error(
                    "All attempts to retrieve or create a Chatbot failed. Using in-memory fallback Chatbot."
                )
                chatbot = Chatbot(name="Fallback", botname="Computer")
            # Ensure chatbot has an id and botname
            if not hasattr(chatbot, "id") or chatbot.id is None:
                chatbot.id = 0
            if not hasattr(chatbot, "botname") or chatbot.botname is None:
                chatbot.botname = "Computer"
            chatbot_id = chatbot.id
            chatbot_botname = chatbot.botname
        else:
            chatbot_id = getattr(chatbot, "id", 0)
            chatbot_botname = getattr(chatbot, "botname", "Computer")
        if chatbot_id is None:
            logger.error(
                "Failed to create or retrieve a valid Chatbot. Conversation creation aborted."
            )
            return None

        # Ensure a valid user exists
        if not user:
            if previous_conversation:
                user = User.objects.get(previous_conversation.user_id)
            if not user:
                user = User.objects.first()
            if not user:
                user_dc = User.objects.create(username="User")
                user_id = user_dc.id
                user_username = user_dc.username
            else:
                user_id = user.id
                user_username = user.username
        else:
            user_id = user.id
            user_username = user.username

        conversation = cls.objects.create(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            title="",
            key="",
            value=[],  # Always use empty list, not None
            chatbot_id=chatbot_id,
            user_id=user_id,
            chatbot_name=chatbot_botname,
            user_name=user_username,
        )
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
            logger.error(f"Error in most_recent(): {e}")

    @classmethod
    def make_current(cls, conversation_id):
        Conversation.objects.update_by({"current": True}, current=False)
        Conversation.objects.update(conversation_id, current=True)


Conversation.summaries = relationship(
    "Summary", order_by=Summary.id, back_populates="conversation"
)
