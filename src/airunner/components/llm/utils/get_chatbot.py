from airunner.models.chatbot import Chatbot
from airunner.utils.application.get_logger import get_logger


def get_chatbot():
    """Return the current chatbot. Creates a default if none exists."""
    eager_load = [
        "target_files",
        "target_directories",
    ]
    try:
        chatbot = Chatbot.objects.filter_by_first(
            eager_load=eager_load, current=True
        )
        if chatbot is None:
            chatbot = Chatbot.objects.first(eager_load=eager_load)
        if chatbot is None:
            chatbot = Chatbot.objects.create(name="Default")
            if chatbot is not None:
                Chatbot.make_current(chatbot.id)
                chatbot = Chatbot.objects.first(eager_load=eager_load)
        if chatbot is None:
            get_logger("get_chatbot").warning(
                "Failed to create default chatbot"
            )
            return None
        return chatbot
    except Exception as e:
        get_logger("get_chatbot").error(f"Error getting chatbot: {e}")
        return None
