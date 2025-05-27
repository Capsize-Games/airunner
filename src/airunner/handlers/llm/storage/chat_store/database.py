import datetime
from typing import Optional, List
from urllib.parse import urlparse
from sqlalchemy.orm.attributes import flag_modified

from llama_index.core.llms import ChatMessage
from llama_index.core.storage.chat_store.base import BaseChatStore
from llama_index.core.base.llms.types import TextBlock

from airunner.data.models import Conversation
from airunner.utils.llm import strip_names_from_message


class SafeChatMessage(ChatMessage):
    @property
    def content(self) -> str:
        content = ""
        for block in self.blocks:
            if hasattr(block, "text"):
                content += block.text or ""
        return content


class DatabaseChatStore(BaseChatStore):
    def set_messages(self, key: str, messages: list[SafeChatMessage]) -> None:
        """Set messages for a key."""
        index = int(key)
        from airunner.data.session_manager import session_scope

        with session_scope() as session:
            conversation = (
                session.query(Conversation).filter(Conversation.id == index).first()
            )
            if conversation:
                if messages and len(messages) > 0:
                    formatted_messages = []
                    for message in messages:
                        message.blocks[0].text = strip_names_from_message(
                            message.blocks[0].text,
                            conversation.user_name,
                            conversation.chatbot_name,
                        )
                        formatted_messages.append(message.model_dump())
                    messages = formatted_messages

                    conversation.value = messages
                    flag_modified(conversation, "value")
                    session.commit()
                else:
                    conversation.value = []
                    flag_modified(conversation, "value")
                    session.commit()
            else:
                conversation = Conversation(
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    title="",
                    key=key,
                    value=messages,
                )
                session.add(conversation)
                session.commit()

    @staticmethod
    def get_latest_chatstore() -> dict:
        """Get the latest chatstore."""
        result = Conversation.objects.order_by("id", "desc").first()
        return (
            {
                "key": str(result.id),
                "value": result.value,
            }
            if result
            else None
        )

    @staticmethod
    def get_chatstores() -> list[dict]:
        """Get all chatstores."""
        result = Conversation.objects.all()
        return [
            {
                "key": str(item.id),
                "value": item.value,
            }
            for item in result
        ]

    def get_messages(self, key: str) -> list[SafeChatMessage]:
        """Get messages for a key."""
        index = int(key)
        result = Conversation.objects.get(index)
        messages = (result.value if result else None) or []
        formatted_messages = []
        for i, message in enumerate(messages):
            role = message.get("role")
            if not isinstance(role, str) or not role:
                role = "user"
            blocks = message.get("blocks")
            sanitized_blocks = []
            if isinstance(blocks, list) and len(blocks) > 0:
                for b in blocks:
                    text = b.get("text") if isinstance(b, dict) else ""
                    if not isinstance(text, str):
                        text = ""
                    sanitized_blocks.append(TextBlock(text=text))
            if not sanitized_blocks:
                sanitized_blocks = [TextBlock(text="")]
            try:
                chat_msg = SafeChatMessage(role=role, blocks=sanitized_blocks)
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to construct SafeChatMessage at index {i}: {message} ({e})"
                )
                chat_msg = SafeChatMessage(role=role, blocks=[TextBlock(text="")])
            formatted_messages.append(chat_msg)
        return formatted_messages

    def add_message(self, key: str, message: SafeChatMessage) -> None:
        """Add a message to a conversation."""
        index = int(key)
        from airunner.data.session_manager import session_scope

        with session_scope() as session:
            conversation = (
                session.query(Conversation).filter(Conversation.id == index).first()
            )
            if conversation:
                messages = conversation.value or []
            else:
                messages = []
            # Remove whitespace from front of message
            message.blocks[0].text = message.blocks[0].text.lstrip()
            # Append the new message
            message.blocks[0].text = strip_names_from_message(
                message.blocks[0].text,
                conversation.user_name if conversation else None,
                conversation.chatbot_name if conversation else None,
            )
            messages.append(message.model_dump())
            if conversation:
                conversation.value = messages
                flag_modified(conversation, "value")
                session.commit()
            else:
                conversation = Conversation(
                    key=key,
                    value=messages,
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
                session.add(conversation)
                session.commit()

    def delete_messages(self, key: str) -> Optional[List[SafeChatMessage]]:
        """Delete messages for a key."""
        index = int(key)
        Conversation.objects.delete(index)
        return None

    def delete_message(self, key: str, message_index: int) -> None:
        """Delete a message from a conversation."""
        index = int(key)
        from airunner.data.session_manager import session_scope

        with session_scope() as session:
            conversation = (
                session.query(Conversation).filter(Conversation.id == index).first()
            )
            if conversation:
                messages = conversation.value or []
                if 0 <= message_index < len(messages):
                    del messages[message_index]
                    conversation.value = messages
                    flag_modified(conversation, "value")
                    session.commit()

    def delete_last_message(self, key: str) -> Optional[SafeChatMessage]:
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
        Conversation.objects.update(index, {"value": messages})
        return SafeChatMessage.model_validate(removed_message)

    def get_keys(self) -> list[str]:
        """Get all keys."""
        conversations = Conversation.objects.all()
        return [str(conversation.id) for conversation in conversations]

    def update_message(
        self, key: str, message_index: int, new_message: SafeChatMessage
    ) -> None:
        """Update a message in a conversation."""
        index = int(key)
        from airunner.data.session_manager import session_scope

        with session_scope() as session:
            conversation = (
                session.query(Conversation).filter(Conversation.id == index).first()
            )
            if conversation:
                messages = conversation.value or []
                if 0 <= message_index < len(messages):
                    new_message.blocks[0].text = strip_names_from_message(
                        new_message.blocks[0].text,
                        conversation.user_name,
                        conversation.chatbot_name,
                    )
                    messages[message_index] = new_message.model_dump()
                    conversation.value = messages
                    flag_modified(conversation, "value")
                    session.commit()


def params_from_uri(uri: str) -> dict:
    result = urlparse(uri)
    database = result.path[1:]
    return {
        "database": database,
    }
