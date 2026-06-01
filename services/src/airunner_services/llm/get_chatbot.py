"""Service-owned chatbot selection helper."""

from types import SimpleNamespace

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.utils.application.get_logger import get_logger


def _fallback_chatbot() -> SimpleNamespace:
    """Return a minimal chatbot-like object for service-only runtimes."""
    return SimpleNamespace(
        id=None,
        name="Default",
        botname="Computer",
        gender="Male",
        voice_id=None,
        current=True,
    )


def get_chatbot():
    """Return the current chatbot or create one default chatbot."""
    eager_load = ["target_files", "target_directories"]
    try:
        chatbot = Chatbot.objects.filter_by_first(
            eager_load=eager_load,
            current=True,
        )
        if chatbot is None:
            chatbot = Chatbot.objects.first(eager_load=eager_load)
        if chatbot is None:
            chatbot = Chatbot.objects.create(name="Foobar")
            Chatbot.make_current(chatbot.id)
            chatbot = Chatbot.objects.first(eager_load=eager_load)
        return chatbot
    except Exception as exc:
        get_logger("get_chatbot").error(
            f"Error getting chatbot: {exc}"
        )
        return _fallback_chatbot()