from typing import Any, Optional
from urllib.parse import urlparse
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql import select
from llama_index.core.llms import ChatMessage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.storage.chat_store.base import BaseChatStore
from airunner.data.models import Conversation
from airunner.utils.strip_names_from_message import strip_names_from_message
from airunner.settings import DB_URL, ASYNC_DB_URL
from airunner.data.session_manager import session_scope

class SQLiteChatStore(BaseChatStore):
    table_name: Optional[str] = Field(
        default="chatstore", description="SQLite table name."
    )
    schema_name: Optional[str] = Field(
        default="", description="SQLite schema name."
    )

    _table_class: Optional[Any] = PrivateAttr()

    def __init__(
        self,
        table_name: str,
        schema_name: str = "",
        use_jsonb: bool = False,
    ):
        super().__init__(
            table_name=table_name.lower(),
            schema_name=schema_name.lower(),
        )

    @classmethod
    def from_params(
        cls,
        database: Optional[str] = None,
        table_name: str = "chatstore",
        schema_name: str = "",
        connection_string: Optional[str] = None,
        async_connection_string: Optional[str] = None,
        debug: bool = False,
        use_jsonb: bool = False,
    ) -> "SQLiteChatStore":
        """Return connection string from database parameters."""
        return cls(
            table_name=table_name,
            schema_name=schema_name,
            use_jsonb=use_jsonb,
        )

    @classmethod
    def from_uri(
        cls,
        uri: str,
        table_name: str = "chatstore",
        schema_name: str = "",
        debug: bool = False,
        use_jsonb: bool = False,
    ) -> "SQLiteChatStore":
        """Return connection string from database parameters."""
        params = params_from_uri(uri)
        return cls.from_params(
            **params,
            table_name=table_name,
            schema_name=schema_name,
            debug=debug,
            use_jsonb=use_jsonb,
        )

    @classmethod
    def _connect(
        cls, connection_string: str, async_connection_string: str, debug: bool
    ) -> tuple[sessionmaker, sessionmaker]:
        _engine = create_engine(connection_string, echo=debug)
        session = sessionmaker(_engine)

        _async_engine = create_async_engine(async_connection_string)
        async_session = sessionmaker(_async_engine, class_=AsyncSession)
        return session, async_session

    def set_messages(self, key: str, messages: list[ChatMessage]) -> None:
        """Set messages for a key."""
        with session_scope() as session:
            result = session.execute(
                select(Conversation).filter_by(key=key)
            )
            conversation = result.scalars().first()
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
                    session.add(conversation)
                session.commit()

    def get_latest_chatstore(self) -> dict:
        """Get the latest chatstore."""
        with session_scope() as session:
            result = session.query(Conversation).order_by(
                Conversation.id.desc()
            ).first()
            return {
                "key": result.key,
                "value": result.value,
            } if result else None

    def get_chatstores(self) -> list[dict]:
        """Get all chatstores."""
        with session_scope() as session:
            result = session.query(Conversation).all()
            return [
                {
                    "key": item.key,
                    "value": item.value,
                } for item in result
            ]

    def get_messages(self, key: str) -> list[ChatMessage]:
        """Get messages for a key."""
        with session_scope() as session:
            result = session.query(Conversation).filter_by(key=key).first()
            if result:
                messages = result.value
            else:
                messages = []
            formatted_messages = []
            for message in messages:
                text = message["blocks"][0]["text"]
                if message["role"] == "user":
                    name = result.user_name
                else:
                    name = result.chatbot_name
                text = f"{name}: {text}"
                formatted_messages.append(ChatMessage.from_str(
                    content=text,
                    role=message["role"],
                ))
            return formatted_messages
 
    def add_message(self, key: str, message: ChatMessage) -> None:
        """Add a message for a key."""
        with session_scope() as session:
            # Retrieve the existing messages from the current conversation
            result = session.execute(
                select(Conversation).filter_by(key=key)
            )
            conversation = result.scalars().first()
            if conversation:
                messages = conversation.value
            else:
                messages = []
            messages = messages or []
        
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
                session.add(conversation)
            session.commit()
    
    def delete_messages(self, key: str) -> Optional[list[ChatMessage]]:
        """Delete messages for a key."""
        with session_scope() as session:
            session.query(Conversation).filter_by(key=key).delete()
            session.commit()
        return None

    def delete_message(self, key: str, idx: int) -> Optional[ChatMessage]:
        """Delete specific message for a key."""
        with session_scope() as session:
            # First, retrieve the current list of messages
            conversation = session.query(Conversation).filter_by(key=key).first()
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
        with session_scope() as session:
            # First, retrieve the current list of messages
            conversation = session.query(Conversation).filter_by(key=key).first()
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
            session.query(Conversation).filter_by(key=key).update({"value": messages})
            session.commit()
            return ChatMessage.model_validate(removed_message)

    def get_keys(self) -> list[str]:
        """Get all keys."""
        with session_scope() as session:
            conversations = session.query(Conversation).all()
            return [conversation.key for conversation in conversations]


def params_from_uri(uri: str) -> dict:
    result = urlparse(uri)
    database = result.path[1:]
    return {
        "database": database,
    }
