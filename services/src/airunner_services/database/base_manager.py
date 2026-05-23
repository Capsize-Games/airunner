"""Service-owned SQLAlchemy base manager helpers."""

from typing import Any, List, Optional, TypeVar

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Query, joinedload, subqueryload

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.database.session import session_scope


_T = TypeVar("_T", bound=Any)


class BaseManager:
    """Provide shared ORM query helpers for model classes."""

    def __init__(self, cls):
        self.cls = cls
        self.logger = get_logger(cls.__name__, AIRUNNER_LOG_LEVEL)

    def _apply_eager_load(
        self,
        query: Query,
        eager_load: Optional[List[str]],
    ) -> Query:
        if eager_load:
            for relationship in eager_load:
                try:
                    rel_attr = getattr(self.cls, relationship)
                    if hasattr(rel_attr, "property") and hasattr(
                        rel_attr.property,
                        "direction",
                    ):
                        query = query.options(subqueryload(rel_attr))
                except AttributeError:
                    self.logger.warning(
                        "Class %s does not have relationship %s",
                        self.cls.__name__,
                        relationship,
                    )
                except Exception as exc:
                    self.logger.error(
                        "Error applying eager load for relationship %s: %s",
                        relationship,
                        exc,
                    )
        return query

    def get(self, pk, eager_load: Optional[List[str]] = None) -> Optional[_T]:
        with session_scope() as session:
            if self.cls.__name__ == "Chatbot" and eager_load is None:
                mapper = inspect(self.cls)
                eager_load = [rel.key for rel in mapper.relationships]
            query = session.query(self.cls)
            query = self._apply_eager_load(query, eager_load)
            result = query.filter(self.cls.id == pk).first()
            session.expunge_all()
            return result.to_dataclass() if result else None

    def get_orm(
        self,
        pk,
        eager_load: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """Return one live ORM instance for update and delete operations."""
        with session_scope() as session:
            try:
                query = session.query(self.cls)
                query = self._apply_eager_load(query, eager_load)
                return query.filter(self.cls.id == pk).first()
            except Exception as exc:
                self.logger.error("Error in get_orm(%s): %s", pk, exc)
                return None

    def first(self, eager_load: Optional[List[str]] = None) -> Optional[_T]:
        with session_scope() as session:
            if self.cls.__name__ == "Chatbot" and eager_load is None:
                mapper = inspect(self.cls)
                eager_load = [rel.key for rel in mapper.relationships]
            query = session.query(self.cls)
            query = self._apply_eager_load(query, eager_load)
            result = query.first()
            session.expunge_all()
            return result.to_dataclass() if result else None

    def get_or_create(self, defaults: Optional[dict] = None, **kwargs) -> _T:
        """Get one existing record or create and return a new one."""
        with session_scope() as session:
            try:
                if kwargs:
                    result = session.query(self.cls).filter_by(**kwargs).first()
                else:
                    result = session.query(self.cls).first()

                if result:
                    session.expunge(result)
                    return result

                create_kwargs = {**(defaults or {}), **kwargs}
                result = self.cls(**create_kwargs)
                session.add(result)
                session.commit()
                session.refresh(result)
                session.expunge(result)
                return result
            except Exception as exc:
                self.logger.error("Error in get_or_create(%s): %s", kwargs, exc)
                raise

    def create(self, **kwargs) -> Optional[_T]:
        """Create one record and return its detached dataclass form."""
        with session_scope() as session:
            try:
                result = self.cls(**kwargs)
                session.add(result)
                session.commit()
                session.refresh(result)
                session.expunge(result)
                return result.to_dataclass()
            except Exception as exc:
                self.logger.error("Error in create(%s): %s", kwargs, exc)
                return None

    def update(self, pk=None, **kwargs) -> bool:
        """Update one record by id and return whether it succeeded."""
        record_id = kwargs.pop("pk", pk)
        if not kwargs:
            return False

        with session_scope() as session:
            try:
                query = session.query(self.cls)
                if record_id is None:
                    result = query.first()
                else:
                    result = query.filter(self.cls.id == record_id).first()

                if result is None:
                    return False

                for key, value in kwargs.items():
                    setattr(result, key, value)

                session.add(result)
                session.commit()
                return True
            except Exception as exc:
                self.logger.error(
                    "Error in update(%s, %s): %s",
                    record_id,
                    kwargs,
                    exc,
                )
                return False

    def all(self) -> List[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as exc:
                self.logger.error("Error in all(): %s", exc)
                return []

    def filter_by(self, **kwargs) -> Optional[List[_T]]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as exc:
                self.logger.error("Error in filter_by(%s): %s", kwargs, exc)
                return None

    def filter_first(self, *args) -> Optional[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args).first()
                session.expunge_all()
                return result.to_dataclass() if result else None
            except Exception as exc:
                self.logger.error("Error in filter(%s): %s", args, exc)
                return None

    def filter(self, *args) -> Optional[List[_T]]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args).all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as exc:
                self.logger.error("Error in filter(%s): %s", args, exc)
                return None

    def filter_by_first(
        self,
        eager_load: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[_T]:
        with session_scope() as session:
            try:
                query = session.query(self.cls)
                if eager_load:
                    for relationship in eager_load:
                        try:
                            query = query.options(
                                joinedload(getattr(self.cls, relationship))
                            )
                        except AttributeError:
                            self.logger.warning(
                                "Class %s does not have relationship %s",
                                self.cls.__name__,
                                relationship,
                            )
                result = query.filter_by(**kwargs).first()
                session.expunge_all()
                return result.to_dataclass() if result else None
            except Exception as exc:
                self.logger.error("Error in filter_by(%s): %s", kwargs, exc)
                return None

    def order_by(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).order_by(*args)
                session.expunge_all()
                return result
            except Exception as exc:
                self.logger.error("Error in order_by(%s): %s", args, exc)
                return None

    def options(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).options(*args)
                session.expunge_all()
                return result
            except Exception as exc:
                self.logger.error("Error in options(%s): %s", args, exc)
                return None

    def delete_all(self) -> int:
        with session_scope() as session:
            try:
                result = session.query(self.cls).delete()
                session.commit()
                return result
            except Exception as exc:
                self.logger.error("Error in delete(): %s", exc)
                return 0

    def delete_by(self, **kwargs) -> bool:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).delete()
                session.commit()
                return result
            except Exception as exc:
                self.logger.error("Error in delete_by(%s): %s", kwargs, exc)
                return False


__all__ = ["BaseManager"]