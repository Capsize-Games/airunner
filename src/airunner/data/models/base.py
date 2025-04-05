from functools import lru_cache
import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect

from airunner.data.session_manager import session_scope
from airunner.data.models.base_manager import BaseManager

Base = declarative_base()
logger = logging.getLogger(__name__)


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
                logger.debug(f"Saved {self}")
            except Exception as e:
                logger.error(f"Error in save(): {e}")
            finally:
                session.expunge(self)

    def delete(self):
        success = False
        with session_scope() as session:
            try:
                session.delete(self)
                session.commit()
                logger.debug(f"Deleted {self.cls}")
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
