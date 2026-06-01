from airunner.daemon_client.resource_store import get_resource_store
from airunner.utils.application.get_logger import get_logger


def get_chatbot():
    """Return the current chatbot. Creates a default if none exists."""
    resource_store = get_resource_store()
    eager_load = [
        "target_files",
        "target_directories",
    ]
    try:
        chatbot = resource_store.first(
            "Chatbot",
            eager_load=eager_load,
            filters={"current": True},
        )
        if chatbot is None:
            chatbot = resource_store.first("Chatbot", eager_load=eager_load)
        if chatbot is None:
            chatbot = resource_store.create(
                "Chatbot",
                {"name": "Default", "current": True},
            )
            if chatbot is not None:
                chatbot = resource_store.first(
                    "Chatbot",
                    eager_load=eager_load,
                    filters={"id": chatbot.id},
                )
        if chatbot is None:
            get_logger("get_chatbot").warning(
                "Failed to create default chatbot"
            )
            return None
        return chatbot
    except Exception as e:
        get_logger("get_chatbot").error(f"Error getting chatbot: {e}")
        return None
