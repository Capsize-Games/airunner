"""Canonical SQLAlchemy declarative base with a swappable objects factory."""

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
    _reset_model_objects_cache()


def _get_objects_factory() -> Type:
    """Return the currently-registered manager factory class.

    The GUI must register its daemon-backed manager during startup
    before any model queries are attempted.
    """
    global _objects_factory
    if _objects_factory is None:
        raise RuntimeError(
            "No objects factory configured. Call set_objects_factory() "
            "during GUI startup before accessing model managers."
        )
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
        from airunner.model_to_dataclass import (  # noqa: PLC0415
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


def _reset_model_objects_cache() -> None:
    """Clear cached manager instances after swapping factories."""

    def _walk(model_cls) -> None:
        model_cls._objects = None
        for subclass in model_cls.__subclasses__():
            _walk(subclass)

    _walk(BaseModel)


__all__ = ["Base", "BaseModel", "set_objects_factory"]
