from .api_service_base import APIServiceBase
from airunner.enums import SignalCode


class ChatbotAPIService(APIServiceBase):
    def update_mood(self, mood, emoji):
        self.emit_signal(
            SignalCode.BOT_MOOD_UPDATED, {"mood": mood, "emoji": emoji}
        )

    def show_loading_message(self, message: str):
        """Emit a signal to show a loading/notification message in the chat UI.

        Args:
            message (str): The message to display in the chat UI.
        """
        self.emit_signal(
            SignalCode.MOOD_SUMMARY_UPDATE_STARTED, {"message": message}
        )
