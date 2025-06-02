from typing import Annotated
import json
from llama_index.core.tools import FunctionTool
from airunner.enums import SignalCode
from airunner.data.models import Conversation
from airunner.handlers.llm.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)


class MoodToolsMixin(ToolSingletonMixin):
    """Mixin for mood-related tools."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation = None
        self.conversation_id = None
        self.emit_signal = None
        self.logger = kwargs.get("logger", None)
        self.mood_engine = kwargs.get("mood_engine", None)

    @property
    def mood_tool(self):
        def set_mood(
            mood_description: Annotated[
                str,
                (
                    "A description of the bot's mood. This should be a short phrase or sentence."
                ),
            ],
            emoji: Annotated[
                str,
                ("An emoji representing the bot's mood. Example: 😊, 😢, 😡, etc."),
            ],
        ) -> str:
            conversation = self.conversation
            if conversation and conversation.value:
                # Update the latest assistant message with mood and emoji
                for msg in reversed(conversation.value):
                    if msg.get("role") == "assistant":
                        msg["bot_mood"] = mood_description
                        msg["bot_mood_emoji"] = emoji
                        break
                Conversation.objects.update(
                    self.conversation_id, value=conversation.value
                )
                self.emit_signal(
                    SignalCode.BOT_MOOD_UPDATED,
                    {"mood": mood_description, "emoji": emoji},
                )
                message = f"Mood set to '{mood_description}' {emoji}."
                self.logger.info(message)
                return message
            message = "No assistant message found to update mood."
            self.logger.warning(message)
            return message

        return self._get_or_create_singleton(
            "_mood_tool",
            FunctionTool.from_defaults,
            set_mood,
            return_direct=True,
        )

    def _parse_mood_data(self, mood_data):
        mood_description, emoji = "neutral", "🙂"
        try:
            if isinstance(mood_data, dict):
                mood_description = mood_data.get("mood", mood_description)
                emoji = mood_data.get("emoji", emoji)
            elif (
                hasattr(mood_data, "__class__")
                and getattr(mood_data.__class__, "__name__", None)
                == "AgentChatResponse"
            ):
                meta = getattr(mood_data, "metadata", None)
                if isinstance(meta, dict):
                    mood_description = meta.get("mood", mood_description)
                    emoji = meta.get("emoji", emoji)
                resp = getattr(mood_data, "response", None)
                if resp and isinstance(resp, str):
                    try:
                        parsed = json.loads(resp)
                        if isinstance(parsed, dict):
                            mood_description = parsed.get("mood", mood_description)
                            emoji = parsed.get("emoji", emoji)
                    except Exception:
                        pass
            elif isinstance(mood_data, str):
                try:
                    parsed = json.loads(mood_data)
                    if isinstance(parsed, dict):
                        mood_description = parsed.get("mood", mood_description)
                        emoji = parsed.get("emoji", emoji)
                except Exception:
                    pass
        except Exception:
            pass
        return mood_description, emoji

    def _emit_mood_signal(self, mood_description, emoji):
        if self.conversation and self.conversation.value:
            for idx in range(len(self.conversation.value) - 1, -1, -1):
                msg = self.conversation.value[idx]
                if msg.get("role") == "assistant":
                    if hasattr(self, "emit_signal"):
                        self.emit_signal(
                            SignalCode.BOT_MOOD_UPDATED,
                            {
                                "message_id": idx,
                                "mood": mood_description,
                                "emoji": emoji,
                                "conversation_id": self.conversation.id,
                            },
                        )
                    break

    def _update_mood(self) -> None:
        try:
            conversation = self.conversation
            if not (conversation and conversation.value):
                self.logger.warning("Conversation is missing or invalid.")
                return
            context = getattr(conversation, "formatted_messages", None)
            if not (context and context.strip()):
                self.logger.warning("Formatted messages are missing or empty.")
                return
            mood_data = self.mood_engine.chat(context)
            if mood_data is None:
                mood_description, emoji = "neutral", "🙂"
            else:
                mood_description, emoji = self._parse_mood_data(mood_data)
            if hasattr(self, "mood_tool"):
                self.mood_tool(mood_description, emoji)
            else:
                self.logger.error("Mood tool is not available.")
            if hasattr(self, "_emit_mood_signal"):
                self._emit_mood_signal(mood_description, emoji)
            else:
                self.logger.error("Mood signal emitter is not available.")
        except Exception as e:
            self.logger.error(f"Error updating mood: {e}")
            if hasattr(self, "mood_tool"):
                self.mood_tool("neutral", "🙂")

    def update_mood(self, mood_description: str, emoji: str) -> str:
        return self.mood_tool(mood_description, emoji)
