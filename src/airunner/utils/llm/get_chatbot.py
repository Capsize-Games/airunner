from airunner.data.models.chatbot import Chatbot
from airunner.utils.application.get_logger import get_logger


def get_chatbot():
    """Return the current chatbot, determined by Chatbot.objects.filter_by(current=True). If none exists, create a default chatbot."""
    # Use string-based relationship names for eager loading
    eager_load = [
        "target_files",
        "target_directories",
        "voice_settings",
        "voice_settings.settings",
    ]
    try:
        chatbots = Chatbot.objects.filter_by(
            current=True, eager_load=eager_load
        )
        chatbot = chatbots[0] if chatbots else None
        if chatbot is None:
            chatbot = Chatbot.objects.first(eager_load=eager_load)
        if chatbot is None:
            chatbot = Chatbot.objects.create(name="Foobar")
            Chatbot.make_current(chatbot.id)
            chatbot = Chatbot.objects.first(eager_load=eager_load)
        return chatbot
    except Exception as e:
        get_logger("get_chatbot").error(f"Error getting chatbot: {e}")
        # Create a default chatbot as fallback
        chatbot = Chatbot.objects.create(name="Default")
        Chatbot.make_current(chatbot.id)
        return chatbot
