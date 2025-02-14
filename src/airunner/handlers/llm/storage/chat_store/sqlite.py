import json
from typing import Any, Optional
from urllib.parse import urlparse
import datetime

from sqlalchemy import (
    Index,
    Column,
    Integer,
    UniqueConstraint,
    text,
    delete,
    select,
    create_engine,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from llama_index.core.llms import ChatMessage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.dialects.sqlite import JSON, VARCHAR
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.storage.chat_store.base import BaseChatStore
from airunner.data.models.settings_models import Conversation


class SQLiteChatStore(BaseChatStore):
    table_name: Optional[str] = Field(
        default="chatstore", description="SQLite table name."
    )
    schema_name: Optional[str] = Field(
        default="", description="SQLite schema name."
    )

    _table_class: Optional[Any] = PrivateAttr()
    _session: Optional[sessionmaker] = PrivateAttr()
    _async_session: Optional[sessionmaker] = PrivateAttr()

    def __init__(
        self,
        session: sessionmaker,
        async_session: sessionmaker,
        table_name: str,
        schema_name: str = "",
        use_jsonb: bool = False,
    ):
        super().__init__(
            table_name=table_name.lower(),
            schema_name=schema_name.lower(),
        )

        self._session = session
        self._async_session = async_session

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
        conn_str = connection_string or f"sqlite:///{database}"
        async_conn_str = async_connection_string or f"sqlite+aiosqlite:///{database}"
        session, async_session = cls._connect(conn_str, async_conn_str, debug)
        return cls(
            session=session,
            async_session=async_session,
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
        with self._session() as session:
            if messages is None or len(messages) == 0:
                # Retrieve the existing messages
                result = session.query(Conversation).filter_by(key=key).first()
                print("SET NEW MESSAGES EXISTING CONVERSATION", result.value)
                if result:
                    messages = result.value
                else:
                    messages = []
            else:
                messages = json.dumps([
                    model.model_dump() if type(model) is ChatMessage else 
                        model for model in messages
                ])
            conversation = session.query(Conversation).filter_by(key=key).first()
            print("SETTING CONVERSATION", messages)
            if conversation:
                conversation.value = messages
            else:
                conversation = Conversation(
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    title="",
                    key=key,
                    value=messages
                )
                session.add(conversation)
            session.commit()

    async def aset_messages(self, key: str, messages: list[ChatMessage]) -> None:
        """Async version of Get messages for a key."""
        async with self._async_session() as session:
            if messages is None or len(messages) == 0:
                # Retrieve the existing messages
                result = session.query(Conversation).filter_by(key=key).first()
                if result:
                    messages = result.value
                else:
                    messages = []
            value = json.dumps([
                model.model_dump() if type(model) is ChatMessage else 
                    model for model in messages
            ])
            conversation = await session.query(Conversation).filter_by(key=key).first()
            if conversation:
                conversation.value = value
            else:
                conversation = Conversation(
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    title="",
                    key=key,
                    value=value
                )
                session.add(conversation)
            await session.commit()
    
    def get_latest_chatstore(self) -> dict:
        """Get the latest chatstore."""
        with self._session() as session:
            result = session.query(Conversation).order_by(
                Conversation.id.desc()
            ).first()
            return {
                "key": result.key,
                "value": result.value,
            } if result else None

    def get_chatstores(self) -> list[dict]:
        """Get all chatstores."""
        with self._session() as session:
            result = session.query(Conversation).all()
            return [
                {
                    "key": item.key,
                    "value": item.value,
                } for item in result
            ]

    def get_messages(self, key: str) -> list[ChatMessage]:
        """Get messages for a key."""
        messages = None
        with self._session() as session:
            conversation = session.query(Conversation).filter_by(key=key).first()
            if conversation:
                data = conversation.value or []
                if type(data) is str:
                    messages = json.loads(data)
            return [
                ChatMessage.model_validate(
                    ChatMessage(
                        role=message["role"],
                        content=message["blocks"][0]["text"],
                    )
                ) for message in messages
             ] if messages else []
 
    async def aget_messages(self, key: str) -> list[ChatMessage]:
        """Async version of Get messages for a key."""
        async with self._async_session() as session:
            conversation = await session.query(Conversation).filter_by(key=key).first()
            if conversation:
                messages = json.loads(conversation.value)
            else:
                messages = None
            return [
                ChatMessage.model_validate(
                    ChatMessage(
                        role=message["role"],
                        content=message["blocks"][0]["text"],
                    )
                ) for message in messages
            ]

    def add_message(self, key: str, message: ChatMessage) -> None:
        """Add a message for a key."""
        with self._session() as session:
            # Retrieve the existing messages
            conversation = session.query(Conversation).filter_by(key=key).first()
            if conversation:
                try:
                    messages = json.loads(conversation.value)
                except TypeError:
                    messages = conversation.value
            else:
                messages = []
            messages = [] if messages is None else messages
    
            # Append the new message
            messages.append(message.model_dump())
            session.query(Conversation).filter_by(key=key).update({"value": json.dumps(messages)})
            session.commit()
    
    async def async_add_message(self, key: str, message: ChatMessage) -> None:
        """Async version of Add a message for a key."""
        async with self._async_session() as session:
            # Retrieve the existing messages
            conversation = await session.query(Conversation).filter_by(key=key).first()
            if conversation:
                try:
                    messages = json.loads(conversation.value)
                except TypeError:
                    messages = conversation.value
            else:
                messages = []
            messages = [] if messages is None else messages
    
            # Append the new message
            messages.append(message.model_dump())
            await session.query(Conversation).filter_by(key=key).update({"value": json.dumps(messages)})
            await session.commit()

    def delete_messages(self, key: str) -> Optional[list[ChatMessage]]:
        """Delete messages for a key."""
        with self._session() as session:
            session.query(Conversation).filter_by(key=key).delete()
            session.commit()
        return None

    async def adelete_messages(self, key: str) -> Optional[list[ChatMessage]]:
        """Async version of Delete messages for a key."""
        async with self._async_session() as session:
            await session.query(Conversation).filter_by(key=key).delete()
            await session.commit()
        return None

    def delete_message(self, key: str, idx: int) -> Optional[ChatMessage]:
        """Delete specific message for a key."""
        with self._session() as session:
            # First, retrieve the current list of messages
            conversation = session.query(Conversation).filter_by(key=key).first()
            if conversation:
                try:
                    messages = json.loads(conversation.value)
                except TypeError:
                    messages = conversation.value
            else:
                messages = None

            if messages is None or idx < 0 or idx >= len(messages):
                # If the key doesn't exist or the index is out of bounds
                return None
            
            # Remove the message at the given index
            removed_message = messages[idx]
            messages.pop(idx)
            session.query(Conversation).filter_by(key=key).update({"value": json.dumps(messages)})
            session.commit()
            return ChatMessage.model_validate(removed_message)

    async def adelete_message(self, key: str, idx: int) -> Optional[ChatMessage]:
        """Async version of Delete specific message for a key."""
        async with self._async_session() as session:
            # First, retrieve the current list of messages
            conversation = await session.query(Conversation).filter_by(key=key).first()
            if conversation:
                try:
                    messages = json.loads(conversation.value)
                except TypeError:
                    messages = conversation.value
            else:
                messages = None

            if messages is None or idx < 0 or idx >= len(messages):
                # If the key doesn't exist or the index is out of bounds
                return None
            
            # Remove the message at the given index
            removed_message = messages[idx]
            messages.pop(idx)
            await session.query(Conversation).filter_by(key=key).update({"value": json.dumps(messages)})
            await session.commit()
            return ChatMessage.model_validate(removed_message)

    def delete_last_message(self, key: str) -> Optional[ChatMessage]:
        """Delete last message for a key."""
        with self._session() as session:
            # First, retrieve the current list of messages
            conversation = session.query(Conversation).filter_by(key=key).first()
            if conversation:
                try:
                    messages = json.loads(conversation.value)
                except TypeError:
                    messages = conversation.value
            else:
                messages = None

            if messages is None or len(messages) == 0:
                # If the key doesn't exist or the array is empty
                return None
            
            # Remove the message at the given index
            removed_message = messages[-1]
            messages.pop(-1)
            session.query(Conversation).filter_by(key=key).update({"value": json.dumps(messages)})
            session.commit()
            return ChatMessage.model_validate(removed_message)

    async def adelete_last_message(self, key: str) -> Optional[ChatMessage]:
        """Async version of Delete last message for a key."""
        async with self._async_session() as session:
            # First, retrieve the current list of messages
            conversation = await session.query(Conversation).filter_by(key=key).first()
            if conversation:
                try:
                    messages = json.loads(conversation.value)
                except TypeError:
                    messages = conversation.value
            else:
                messages = None

            if messages is None or len(messages) == 0:
                # If the key doesn't exist or the array is empty
                return None
            
            # Remove the message at the given index
            removed_message = messages[-1]
            messages.pop(-1)
            await session.query(Conversation).filter_by(key=key).update({"value": json.dumps(messages)})
            await session.commit()
            return ChatMessage.model_validate(removed_message)

    def get_keys(self) -> list[str]:
        """Get all keys."""
        with self._session() as session:
            conversations = session.query(Conversation).all()
            return [conversation.key for conversation in conversations]

    async def aget_keys(self) -> list[str]:
        """Async version of Get all keys."""
        async with self._async_session() as session:
            conversations = await session.query(Conversation).all()
            return [conversation.key for conversation in conversations]


def params_from_uri(uri: str) -> dict:
    result = urlparse(uri)
    database = result.path[1:]
    return {
        "database": database,
    }
