"""Canonical SQLAlchemy declarative base with lazy objects factory.

The ``objects`` manager on every model subclass is created lazily on
first access so that the same model definitions work for both the
real ORM (api) and the HTTP bridge (services / src / GUI).  The
factory is configured once at startup before any queries are issued.

Usage::

    # service (has direct database access)
    from airunner_services.database.base_manager import RealBaseManager
    from airunner_services.database.base import set_objects_factory
    set_objects_factory(RealBaseManager)

    # services / src (talks to api)
    from airunner_model.bridge_manager import BridgeBaseManager
    from airunner_services.database.base import set_objects_factory
    set_objects_factory(BridgeBaseManager)

Models are defined in ``airunner_services.database.models`` and inherit from
``BaseModel``.  No changes are needed in individual model files when
switching between real ORM and bridge mode.
"""

from __future__ import annotations

from functools import lru_cache
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import declarative_base
from typing import Type

# ---------------------------------------------------------------------------
# Lazy objects factory
# ---------------------------------------------------------------------------
_objects_factory: Type | None = None


def set_objects_factory(factory: Type) -> None:
    """Register the manager class used by every model's ``.objects``.

    Must be called once at startup, *before* any model query is
    executed.  The factory receives one argument -- the model class
    -- and must return a manager instance.

    The safe default when this function is never called is
    ``RealBaseManager``, which is appropriate for the api layer.
    """
    global _objects_factory  # noqa: PLW0603
    _objects_factory = factory


def _get_objects_factory() -> Type:
    """Return the currently-registered manager factory class.

    When no factory has been registered the real ORM manager is used,
    which is the correct default for the api layer.
    """
    global _objects_factory
    if _objects_factory is None:
        from airunner_services.database.base_manager import (  # noqa: PLC0415
            RealBaseManager,
        )

        _objects_factory = RealBaseManager
    return _objects_factory


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
Base = declarative_base()

# ---------------------------------------------------------------------------
# classproperty descriptor (replaces @classmethod @property)
# ---------------------------------------------------------------------------


class classproperty:
    """Descriptor that acts like @property but on the class itself.

    Usage::

        class MyModel(BaseModel):
            @classproperty
            def objects(cls):
                ...
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, cls=None):
        if cls is None:
            cls = type(obj)
        return self.fget(cls)


# ---------------------------------------------------------------------------
# BaseModel
# ---------------------------------------------------------------------------


class BaseModel(Base):
    """Common ORM model base with lazy objects manager.

    Subclasses automatically receive a ``cls.objects`` attribute
    on first access.  The underlying manager is determined by the
    factory registered via ``set_objects_factory()``.
    """

    __abstract__ = True

    _objects = None

    # ------------------------------------------------------------------
    # Lazy manager (populated on first access)
    # ------------------------------------------------------------------
    @classproperty
    def objects(cls):
        """Return the manager instance for this model class."""
        if cls._objects is None:
            cls._objects = _get_objects_factory()(cls)
        return cls._objects

    # ------------------------------------------------------------------
    # Dataclass helpers
    # ------------------------------------------------------------------
    @classmethod
    @lru_cache(maxsize=None)
    def get_dataclass(cls):
        """Get or generate the dataclass for one ORM model class."""
        from airunner_services.database.model_to_dataclass import (  # noqa: PLC0415
            model_to_dataclass,
        )

        return model_to_dataclass(cls)

    # ------------------------------------------------------------------
    # Persistence helpers (work with real ORM and bridge alike)
    # ------------------------------------------------------------------
    def save(self):
        """Persist one model instance."""
        self.objects.save(self)

    def delete(self):
        """Delete one model instance and return success."""
        return self.objects.delete_instance(self)

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------
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


__all__ = ["Base", "BaseModel", "set_objects_factory"]
