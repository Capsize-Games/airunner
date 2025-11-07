from functools import lru_cache
from sqlalchemy.orm import declarative_base
from sqlalchemy.inspection import inspect

from airunner.components.data.session_manager import session_scope
from airunner.components.data.models.base_manager import BaseManager
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

Base = declarative_base()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class BaseModel(Base):
    __abstract__ = True

    @classmethod
    @lru_cache(maxsize=None)
    def get_dataclass(cls):
        """Get or generate the dataclass for this model."""
        # Delay the import to avoid circular dependency
        from airunner.utils.data.model_to_dataclass import model_to_dataclass

        return model_to_dataclass(cls)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.objects = BaseManager(cls)

    def save(self):
        with session_scope() as session:
            session.add(self)
            try:
                session.commit()
                session.refresh(self)
            except Exception as e:
                logger.error(f"Error in save(): {e}")

    def delete(self):
        success = False
        with session_scope() as session:
            try:
                session.delete(self)
                session.commit()
                success = True
            except Exception as e:
                logger.error(f"Error in delete(): {e}")
            session.expunge(self)
        return success

    def to_dataclass(self) -> object:
        """Convert the model instance to its corresponding dataclass."""
        dataclass_cls = self.get_dataclass()
        return dataclass_cls(**self.to_dict())

    def to_dict(self):
        return {
            c.key: getattr(self, c.key)
            for c in inspect(self).mapper.column_attrs
        }
