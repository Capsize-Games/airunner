import json
from typing import Any, Optional
from urllib.parse import urlparse

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


def get_data_model(
    base: type,
    index_name: str,
    schema_name: str,
    use_jsonb: bool = False,
) -> Any:
    """
    This part create a dynamic sqlalchemy model with a new table.
    """
    tablename = f"data_{index_name}"  # dynamic table name
    class_name = f"Data{index_name}"  # dynamic class name

    chat_dtype = JSON

    class AbstractData(base):  # type: ignore
        __abstract__ = True  # this line is necessary
        id = Column(Integer, primary_key=True, autoincrement=True)  # Add primary key
        key = Column(VARCHAR, nullable=False)
        value = Column(chat_dtype)

    return type(
        class_name,
        (AbstractData,),
        {
            "__tablename__": tablename,
            "__table_args__": (
                UniqueConstraint("key", name=f"{tablename}:unique_key"),
                Index(f"{tablename}:idx_key", "key"),
            ),
        },
    )


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

        # sqlalchemy model
        base = declarative_base()
        self._table_class = get_data_model(
            base,
            table_name,
            schema_name,
            use_jsonb=use_jsonb,
        )
        self._session = session
        self._async_session = async_session
        self._initialize(base)

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

    def _create_schema_if_not_exists(self) -> None:
        # SQLite does not support schemas, so this method can be skipped
        pass

    def _create_tables_if_not_exists(self, base) -> None:
        with self._session() as session, session.begin():
            base.metadata.create_all(session.connection())

    def _initialize(self, base) -> None:
        self._create_tables_if_not_exists(base)

    def set_messages(self, key: str, messages: list[ChatMessage]) -> None:
        """Set messages for a key."""
        with self._session() as session:
            if messages is None or len(messages) == 0:
                # Retrieve the existing messages
                result = session.execute(select(self._table_class).filter_by(key=key)).scalars().first()
                if result:
                    messages = result.value
                else:
                    messages = []
                
            # Update the database with the new list of messages
            stmt = text(
                f"""
                INSERT INTO {self._table_class.__tablename__} (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = :value;
                """
            )
            params = {
                "key": key, 
                "value": json.dumps([
                    model.model_dump() if type(model) is ChatMessage else 
                        model for model in messages
                ])}
            try:
                session.execute(stmt, params)
                session.commit()
            except Exception as e:
                print(e)

    async def aset_messages(self, key: str, messages: list[ChatMessage]) -> None:
        """Async version of Get messages for a key."""
        async with self._async_session() as session:
            stmt = text(
                f"""
                INSERT INTO {self._table_class.__tablename__} (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key)
                DO UPDATE SET
                value = EXCLUDED.value;
                """
            )

            params = {
                "key": key,
                "value": json.dumps([
                    message.model_dump() for message in messages
                ]),
            }

            # Execute the bulk upsert
            await session.execute(stmt, params)
            await session.commit()

    def get_messages(self, key: str) -> list[ChatMessage]:
        """Get messages for a key."""
        with self._session() as session:
            result = session.execute(select(self._table_class).filter_by(key=key))
            result = result.scalars().first()
            if result:
                if result:
                    messages = result.value
            else:
                messages = None
            return [
                ChatMessage.model_validate(
                    ChatMessage(
                        role=message["role"],
                        content=message["blocks"][0]["text"],
                    )
                ) for message in messages
             ] if messages else None
 
    async def aget_messages(self, key: str) -> list[ChatMessage]:
        """Async version of Get messages for a key."""
        async with self._async_session() as session:
            result = await session.execute(select(self._table_class).filter_by(key=key))
            result = result.scalars().first()
            if result:
                messages = json.loads(result.value)
            else:
                messages = []
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
            result = session.execute(select(self._table_class).filter_by(key=key)).scalars().first()
            if result:
                try:
                    messages = json.loads(result.value)
                except TypeError:
                    messages = result.value
            else:
                messages = []
    
            # Append the new message
            messages.append(message.model_dump())
    
            # Update the database with the new list of messages
            stmt = text(
                f"""
                INSERT INTO {self._table_class.__tablename__} (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = :value;
                """
            )
            params = {"key": key, "value": json.dumps(messages)}
            try:
                session.execute(stmt, params)
                session.commit()
            except Exception as e:
                print(e)
    
    async def async_add_message(self, key: str, message: ChatMessage) -> None:
        """Async version of Add a message for a key."""
        async with self._async_session() as session:
            # Retrieve the existing messages
            result = await session.execute(select(self._table_class).filter_by(key=key))
            result = result.scalars().first()
            if result:
                messages = json.loads(result.value)
            else:
                messages = []
    
            # Append the new message
            messages.append(message.model_dump())
    
            # Update the database with the new list of messages
            stmt = text(
                f"""
                INSERT INTO {self._table_class.__tablename__} (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = :value;
                """
            )
            params = {"key": key, "value": json.dumps(messages)}
            try:
                await session.execute(stmt, params)
                await session.commit()
            except Exception as e:
                print(e)
            await session.commit()

    def delete_messages(self, key: str) -> Optional[list[ChatMessage]]:
        """Delete messages for a key."""
        with self._session() as session:
            session.execute(delete(self._table_class).filter_by(key=key))
            session.commit()
        return None

    async def adelete_messages(self, key: str) -> Optional[list[ChatMessage]]:
        """Async version of Delete messages for a key."""
        async with self._async_session() as session:
            await session.execute(delete(self._table_class).filter_by(key=key))
            await session.commit()
        return None

    def delete_message(self, key: str, idx: int) -> Optional[ChatMessage]:
        """Delete specific message for a key."""
        with self._session() as session:
            # First, retrieve the current list of messages
            stmt = select(self._table_class.value).where(self._table_class.key == key)
            result = session.execute(stmt).scalar_one_or_none()

            if result is None or idx < 0 or idx >= len(result):
                # If the key doesn't exist or the index is out of bounds
                return None

            # Remove the message at the given index
            removed_message = result[idx]

            stmt = text(
                f"""
                UPDATE {self._table_class.__tablename__}
                SET value = json_remove({self._table_class.__tablename__}.value, '$[{idx}]')
                WHERE key = :key;
                """
            )

            params = {"key": key}
            session.execute(stmt, params)
            session.commit()

            return ChatMessage.model_validate(removed_message)

    async def adelete_message(self, key: str, idx: int) -> Optional[ChatMessage]:
        """Async version of Delete specific message for a key."""
        async with self._async_session() as session:
            # First, retrieve the current list of messages
            stmt = select(self._table_class.value).where(self._table_class.key == key)
            result = (await session.execute(stmt)).scalar_one_or_none()

            if result is None or idx < 0 or idx >= len(result):
                # If the key doesn't exist or the index is out of bounds
                return None

            # Remove the message at the given index
            removed_message = result[idx]

            stmt = text(
                f"""
                UPDATE {self._table_class.__tablename__}
                SET value = json_remove({self._table_class.__tablename__}.value, '$[{idx}]')
                WHERE key = :key;
                """
            )

            params = {"key": key}
            await session.execute(stmt, params)
            await session.commit()

            return ChatMessage.model_validate(removed_message)

    def delete_last_message(self, key: str) -> Optional[ChatMessage]:
        """Delete last message for a key."""
        with self._session() as session:
            # First, retrieve the current list of messages
            stmt = select(self._table_class.value).where(self._table_class.key == key)
            result = session.execute(stmt).scalar_one_or_none()

            if result is None or len(result) == 0:
                # If the key doesn't exist or the array is empty
                return None

            # Remove the message at the given index
            removed_message = result[-1]

            stmt = text(
                f"""
                UPDATE {self._table_class.__tablename__}
                SET value = json_remove({self._table_class.__tablename__}.value, '$[#-1]')
                WHERE key = :key;
                """
            )
            params = {"key": key}
            session.execute(stmt, params)
            session.commit()

            return ChatMessage.model_validate(removed_message)

    async def adelete_last_message(self, key: str) -> Optional[ChatMessage]:
        """Async version of Delete last message for a key."""
        async with self._async_session() as session:
            # First, retrieve the current list of messages
            stmt = select(self._table_class.value).where(self._table_class.key == key)
            result = (await session.execute(stmt)).scalar_one_or_none()

            if result is None or len(result) == 0:
                # If the key doesn't exist or the array is empty
                return None

            # Remove the message at the given index
            removed_message = result[-1]

            stmt = text(
                f"""
                UPDATE {self._table_class.__tablename__}
                SET value = json_remove({self._table_class.__tablename__}.value, '$[#-1]')
                WHERE key = :key;
                """
            )
            params = {"key": key}
            await session.execute(stmt, params)
            await session.commit()

            return ChatMessage.model_validate(removed_message)

    def get_keys(self) -> list[str]:
        """Get all keys."""
        with self._session() as session:
            stmt = select(self._table_class.key)

            return session.execute(stmt).scalars().all()

    async def aget_keys(self) -> list[str]:
        """Async version of Get all keys."""
        async with self._async_session() as session:
            stmt = select(self._table_class.key)

            return (await session.execute(stmt)).scalars().all()


def params_from_uri(uri: str) -> dict:
    result = urlparse(uri)
    database = result.path[1:]
    return {
        "database": database,
    }
