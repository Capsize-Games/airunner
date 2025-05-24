from .api_service_base import APIServiceBase
from airunner.enums import SignalCode


class ChatbotAPIService(APIServiceBase):
    def update_mood(self, mood):
        self.emit_signal(SignalCode.BOT_MOOD_UPDATED, {"mood": mood})
