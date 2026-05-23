"""Service-owned conversation model."""

import datetime
import uuid
from typing import Optional

from sqlalchemy import (
	JSON,
	Boolean,
	Column,
	DateTime,
	ForeignKey,
	Integer,
	String,
	Text,
)
from sqlalchemy.orm import relationship
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lex_rank import LexRankSummarizer

from airunner_services.database.base import BaseModel
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.summary import Summary
from airunner_services.database.models.user import User
from airunner_services.database.session import session_scope


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class Conversation(BaseModel):
	"""Persisted conversation transcript and related metadata."""

	__tablename__ = "conversations"

	id = Column(Integer, primary_key=True, autoincrement=True)
	timestamp = Column(
		DateTime,
		default=datetime.datetime.now(datetime.timezone.utc),
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
		"""Return stored conversation messages in summarizer-friendly text."""
		messages = self.value
		if messages:
			context = ""
			for message in messages:
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
		"""Generate a one-sentence summary of the conversation."""
		messages = self.formatted_messages
		if messages != "":
			parser = PlaintextParser.from_string(
				messages,
				Tokenizer("english"),
			)
			summarizer = LexRankSummarizer()
			summary = summarizer(parser.document, 1)
			return "\n".join([str(sentence) for sentence in summary])
		return ""

	@classmethod
	def delete(cls, pk=None, **kwargs):
		"""Delete one conversation and its related summaries."""
		Summary.objects.delete(conversation_id=pk)
		cls.objects.delete(pk, **kwargs)

	@classmethod
	def create(
		cls,
		chatbot: Optional[Chatbot] = None,
		user: Optional[User] = None,
	):
		"""Create one new conversation using current or fallback actors."""
		prev_chatbot_id = None
		prev_user_id = None
		try:
			with session_scope() as session:
				row = (
					session.query(cls.chatbot_id, cls.user_id)
					.order_by(cls.id.desc())
					.first()
				)
				if row:
					prev_chatbot_id, prev_user_id = row
		except Exception as exc:
			logger.error(f"Error retrieving previous conversation: {exc}")

		chatbot_id = None
		chatbot_botname = None
		if not chatbot:
			chatbot = None
			if prev_chatbot_id is not None:
				try:
					chatbot = Chatbot.objects.get(prev_chatbot_id)
				except Exception as exc:
					logger.error(
						"Error retrieving chatbot from previous "
						f"conversation: {exc}"
					)
					chatbot = None
			if not chatbot:
				try:
					chatbot = Chatbot.objects.first()
				except Exception as exc:
					logger.error(f"Error retrieving first chatbot: {exc}")
					chatbot = None
			if not chatbot:
				try:
					unique_name = f"DefaultChatbot_{uuid.uuid4()}"
					chatbot = Chatbot.objects.create(
						name=unique_name,
						botname="Computer",
					)
					Chatbot.make_current(chatbot.id)
				except Exception as exc:
					logger.error(f"Error creating default chatbot: {exc}")
					chatbot = None
			if not chatbot:
				logger.error(
					"All attempts to retrieve or create a Chatbot failed. "
					"Using in-memory fallback Chatbot."
				)
				chatbot = Chatbot(name="Fallback", botname="Computer")
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
				"Failed to create or retrieve a valid Chatbot. "
				"Conversation creation aborted."
			)
			return None

		if not user:
			if prev_user_id:
				try:
					user = User.objects.get(prev_user_id)
				except Exception as exc:
					logger.error(
						"Error retrieving user from previous conversation: "
						f"{exc}"
					)
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

		conversation_dc = cls.objects.create(
			timestamp=datetime.datetime.now(datetime.timezone.utc),
			title="",
			key="",
			value=[],
			chatbot_id=chatbot_id,
			user_id=user_id,
			chatbot_name=chatbot_botname,
			user_name=user_username,
		)
		if conversation_dc and getattr(conversation_dc, "id", None):
			try:
				cls.make_current(conversation_dc.id)
			except Exception:
				pass
		return conversation_dc

	@classmethod
	def most_recent(cls) -> Optional["Conversation"]:
		"""Return the most recently created conversation."""
		try:
			conversation = cls.objects.order_by(cls.id.desc()).first()
			if conversation:
				return Conversation(**conversation.to_dict())
		except Exception as exc:
			logger.error(f"Error in most_recent(): {exc}")
		return None

	@classmethod
	def make_current(cls, conversation_id):
		"""Mark one conversation current and clear the flag on others."""
		Conversation.objects.update_by({"current": True}, current=False)
		Conversation.objects.update(conversation_id, current=True)


Conversation.summaries = relationship(
	"Summary",
	order_by=Summary.id,
	back_populates="conversation",
)

__all__ = ["Conversation"]