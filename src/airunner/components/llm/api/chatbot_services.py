from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class ChatbotAPIService(APIServiceBase):
    def update_mood(self, mood, emoji=None):
        """Emit a signal to update the bot's mood.

        Args:
            mood: The mood value (str, int, or object).
            emoji: Optional emoji representing the mood.
        """
        data = {"mood": mood}
        if emoji is not None:
            data["emoji"] = emoji
        self.emit_signal(SignalCode.BOT_MOOD_UPDATED, data)

    def show_loading_message(self, message: str):
        """Emit a signal to show a loading/notification message in the chat UI.

        Args:
            message (str): The message to display in the chat UI.
        """
        self.emit_signal(
            SignalCode.MOOD_SUMMARY_UPDATE_STARTED, {"message": message}
        )
