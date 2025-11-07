import datetime
from typing import Optional, List
from urllib.parse import urlparse
from sqlalchemy.orm.attributes import flag_modified

from llama_index.core.llms import ChatMessage
from llama_index.core.storage.chat_store.base import BaseChatStore
from llama_index.core.base.llms.types import TextBlock, MessageRole

from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.utils import strip_names_from_message
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


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
        conversation = Conversation.objects.get(index)

        # TODO: Re-enable this protection after fixing streaming
        # Skip updates if messages contain incomplete assistant responses
        # This prevents race conditions during streaming
        # if messages and len(messages) > 0:
        #     last_message = messages[-1]
        #     if (
        #         hasattr(last_message, "role")
        #         and last_message.role == MessageRole.ASSISTANT
        #         and hasattr(last_message, "blocks")
        #         and len(last_message.blocks) > 0
        #         and hasattr(last_message.blocks[0], "text")
        #         and not last_message.blocks[0].text.strip()
        #     ):
        #         print(
        #             f"Skipping database update for conversation {index} - empty assistant message detected"
        #         )
        #         return

        # Protect against incomplete message overwrites - but allow incremental updates
        # Check if the last message is an incomplete assistant message
        if (
            messages
            and len(messages) > 0
            and hasattr(messages[-1], "role")
            and messages[-1].role == MessageRole.ASSISTANT
            and hasattr(messages[-1], "blocks")
            and messages[-1].blocks
            and hasattr(messages[-1].blocks[0], "text")
        ):
            # For incremental updates, allow updates if:
            # 1. Message has explicit is_complete=False (streaming in progress)
            # 2. Message has is_complete=True (final update)
            # 3. Message text is not empty (has actual content)
            last_message = messages[-1]
            message_dict = (
                last_message.model_dump()
                if hasattr(last_message, "model_dump")
                else last_message
            )

            is_complete = message_dict.get(
                "is_complete", True
            )  # Default to complete if not specified
            has_content = last_message.blocks[0].text.strip()

            # Only skip if message is complete but has no content (likely corrupted)
            if is_complete and not has_content:
                return

        if messages and len(messages) > 0:
            formatted_messages = []
            for message in messages:
                message.blocks[0].text = strip_names_from_message(
                    message.blocks[0].text,
                    conversation.user_name if conversation else None,
                    conversation.chatbot_name if conversation else None,
                )
                formatted_messages.append(message.model_dump())
            messages = formatted_messages

            self.update_or_create(conversation, index, messages, key)

    def update_or_create(self, conversation, index, messages, key):
        if conversation:
            Conversation.objects.update(index, value=messages)
        else:
            conversation = Conversation.objects.create(
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                title="",
                key=key,
                value=messages,
            )
            Conversation.make_current(conversation.id)

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
        """Get messages for a key. Returns an empty list if key is None or not a valid integer."""
        if key is None or key == "None":
            return []
        try:
            index = int(key)
        except (TypeError, ValueError):
            return []
        result = Conversation.objects.get(index)
        messages = (result.value if result else None) or []
        formatted_messages = []
        for i, message in enumerate(messages):
            role = message.get("role")
            if not isinstance(role, str) or not role:
                role = "user"
            if role == "bot":
                role = "assistant"
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

                logger.warning(
                    f"Failed to construct SafeChatMessage at index {i}: {message} ({e})"
                )
                chat_msg = SafeChatMessage(
                    role=role, blocks=[TextBlock(text="")]
                )
            formatted_messages.append(chat_msg)
        return formatted_messages

    def add_message(self, key: str, message: SafeChatMessage) -> None:
        """Add a message to a conversation. Throws if duplicate."""
        index = int(key)
        conversation = Conversation.objects.get(index)
        messages = (conversation.value or []) if conversation else []
        if message.blocks and len(message.blocks) > 0:
            message.blocks[0].text = message.blocks[0].text.lstrip()
        message.blocks[0].text = strip_names_from_message(
            message.blocks[0].text,
            conversation.user_name if conversation else None,
            conversation.chatbot_name if conversation else None,
        )
        new_msg = message.model_dump()
        messages.append(new_msg)
        self.update_or_create(conversation, index, messages, key)

    def delete_messages(self, key: str) -> Optional[List[SafeChatMessage]]:
        """Delete messages for a key."""
        index = int(key)
        Conversation.objects.delete(index)
        return None

    def delete_message(self, key: str, message_index: int) -> None:
        """Delete a message from a conversation."""
        index = int(key)
        conversation = Conversation.objects.get(index)
        if conversation:
            messages = conversation.value or []
            if 0 <= message_index < len(messages):
                del messages[message_index]
                Conversation.objects.update(index, value=messages)

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
        Conversation.objects.update(index, value=messages)
        return SafeChatMessage.model_validate(removed_message)

    def get_keys(self) -> list[str]:
        """Get all keys."""
        conversations = Conversation.objects.all()
        return [str(conversation.id) for conversation in conversations]

    def update_message(
        self, key: str, message_index: int, new_message: SafeChatMessage
    ) -> None:
        """Update a message in a conversation."""
        try:
            conversation = Conversation.objects.filter_by(current=True)[0]
        except IndexError:
            conversation = None
        if conversation:
            messages = conversation.value or []
            if 0 <= message_index < len(messages):
                new_message.blocks[0].text = strip_names_from_message(
                    new_message.blocks[0].text,
                    conversation.user_name,
                    conversation.chatbot_name,
                )
                messages[message_index] = new_message.model_dump()
                Conversation.objects.update(conversation.id, value=messages)
                flag_modified(conversation, "value")


def params_from_uri(uri: str) -> dict:
    result = urlparse(uri)
    database = result.path[1:]
    return {
        "database": database,
    }
