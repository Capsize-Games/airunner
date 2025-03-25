import datetime
from typing import Optional, List
from urllib.parse import urlparse
from sqlalchemy.orm.attributes import flag_modified

from llama_index.core.llms import ChatMessage
from llama_index.core.storage.chat_store.base import BaseChatStore

from airunner.data.models import Conversation
from airunner.utils import strip_names_from_message


class DatabaseChatStore(BaseChatStore):
    def set_messages(self, key: str, messages: list[ChatMessage]) -> None:
        """Set messages for a key."""
        index = int(key)
        conversation = Conversation.objects.get(index)
        if conversation:
            if messages and len(messages) > 0:
                formatted_messages = []
                for message in messages:
                    message.blocks[0].text = strip_names_from_message(
                        message.blocks[0].text,
                        conversation.user_name,
                        conversation.chatbot_name
                    )
                    formatted_messages.append(message.model_dump())
                messages = formatted_messages

                if conversation:
                    conversation.value = messages
                    flag_modified(conversation, "value")
                else:
                    conversation = Conversation(
                        timestamp=datetime.datetime.now(datetime.timezone.utc),
                        title="",
                        key=key,
                        value=messages
                    )
                conversation.save()

    @staticmethod
    def get_latest_chatstore() -> dict:
        """Get the latest chatstore."""
        result = Conversation.objects.order_by("id", "desc").first()
        return {
            "key": str(result.id),
            "value": result.value,
        } if result else None

    @staticmethod
    def get_chatstores() -> list[dict]:
        """Get all chatstores."""
        result = Conversation.objects.all()
        return [
            {
                "key": str(item.id),
                "value": item.value,
            } for item in result
        ]

    def get_messages(self, key: str) -> list[ChatMessage]:
        """Get messages for a key."""
        index = int(key)
        result = Conversation.objects.get(index)
        messages = (result.value if result else None) or []
        formatted_messages = []
        for message in messages:
            text = message["blocks"][0]["text"]
            if message["role"] == "user":
                name = result.user_name
            else:
                name = result.chatbot_name
            text = f"{text}"
            formatted_messages.append(ChatMessage.from_str(
                content=text,
                role=message["role"],
            ))
        return formatted_messages
 
    def add_message(self, key: str, message: ChatMessage) -> None:
        """Add a message for a key."""
        index = int(key)
        conversation = Conversation.objects.get(index)
        if conversation:
            messages = conversation.value
        else:
            messages = []
        messages = messages or []

        # Remove whitespace from front of message
        message.blocks[0].text = message.blocks[0].text.lstrip()
    
        # Append the new message
        message.blocks[0].text = strip_names_from_message(
            message.blocks[0].text,
            conversation.user_name,
            conversation.chatbot_name
        )

        # Append the new message
        messages.append(message.model_dump())

        if conversation:
            conversation.value = messages
            flag_modified(conversation, "value")
        else:
            conversation = Conversation(
                key=key,
                value=messages,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                title="",
            )
        conversation.save()
    
    def delete_messages(self, key: str) -> Optional[List[ChatMessage]]:
        """Delete messages for a key."""
        index = int(key)
        Conversation.objects.delete(index)
        return None

    def delete_message(self, key: str, idx: int) -> Optional[ChatMessage]:
        """Delete specific message for a key."""
        index = int(key)
        # First, retrieve the current list of messages
        conversation = Conversation.objects.get(index)
        if conversation:
            messages = conversation.values
        else:
            messages = None

        if messages is None or idx < 0 or idx >= len(messages):
            # If the key doesn't exist or the index is out of bounds
            return None
        
        # Remove the message at the given index
        removed_message = messages[idx]
        messages.pop(idx)
        self._update_conversation(conversation, messages)
        return ChatMessage.model_validate(removed_message)

    def delete_last_message(self, key: str) -> Optional[ChatMessage]:
        """Delete last message for a key."""
        index = int(key)
        # First, retrieve the current list of messages
        conversation = Conversation.objects.get(index)
        if conversation:
            messages = conversation.value
        else:
            messages = None

        if messages is None or len(messages) == 0:
            # If the key doesn't exist or the array is empty
            return None
        
        # Remove the message at the given index
        removed_message = messages[-1]
        messages.pop(-1)
        Conversation.objects.update(index, {
            "value": messages
        })
        return ChatMessage.model_validate(removed_message)

    def get_keys(self) -> list[str]:
        """Get all keys."""
        conversations = Conversation.objects.all()
        return [str(conversation.id) for conversation in conversations]


def params_from_uri(uri: str) -> dict:
    result = urlparse(uri)
    database = result.path[1:]
    return {
        "database": database,
    }
