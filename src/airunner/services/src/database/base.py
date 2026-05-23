"""Service-owned SQLAlchemy declarative base helpers."""

from functools import lru_cache

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import declarative_base

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.data.model_to_dataclass import (
    model_to_dataclass,
)
from airunner_services.utils.application import get_logger
from airunner_services.database.base_manager import BaseManager
from airunner_services.database.session import session_scope


Base = declarative_base()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class BaseModel(Base):
    """Common ORM model base with persistence helpers."""

    __abstract__ = True

    @classmethod
    @lru_cache(maxsize=None)
    def get_dataclass(cls):
        """Get or generate the dataclass for one ORM model class."""
        return model_to_dataclass(cls)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.objects = BaseManager(cls)

    def save(self):
        """Persist one model instance in the current database."""
        with session_scope() as session:
            session.add(self)
            try:
                session.commit()
                session.refresh(self)
            except Exception as exc:
                logger.error("Error in save(): %s", exc)

    def delete(self):
        """Delete one model instance and return whether it succeeded."""
        success = False
        with session_scope() as session:
            try:
                session.delete(self)
                session.commit()
                success = True
            except Exception as exc:
                logger.error("Error in delete(): %s", exc)
            session.expunge(self)
        return success

    def to_dataclass(self) -> object:
        """Convert one ORM instance to its generated dataclass form."""
        dataclass_cls = self.get_dataclass()
        return dataclass_cls(**self.to_dict())

    def to_dict(self):
        """Convert one ORM instance to a dict of mapped columns."""
        return {
            column.key: getattr(self, column.key)
            for column in inspect(self).mapper.column_attrs
        }


__all__ = ["Base", "BaseModel"]