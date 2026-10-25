"""Real ORM BaseManager -- direct SQLAlchemy queries.

Used by the service layer which has direct database access.
Registered as the ``objects`` factory by calling::

    from airunner_services.database.base import set_objects_factory
    from airunner_services.database.base_manager import RealBaseManager
    set_objects_factory(RealBaseManager)
"""

from __future__ import annotations

from typing import Any, List, Optional, TypeVar

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Query, joinedload, subqueryload

from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.database.session import session_scope

_T = TypeVar("_T", bound=Any)

#: Kwarg-name hints whose values must never reach logs verbatim.
SECRET_KEY_HINTS = (
    "secret",
    "api_key",
    "apikey",
    "token",
    "password",
    "passwd",
    "private_key",
)

#: Default page size for unbounded list queries (N+1 guard).
DEFAULT_LIST_LIMIT = 500

#: Refuse single bulk deletes larger than this (row-cap guard).
MAX_BULK_DELETE_ROWS = 1000


def _redacted_kwargs(kwargs: dict) -> dict:
    """Return kwargs with secret-looking values replaced."""
    redacted = {}
    for key, value in kwargs.items():
        lowered = str(key).lower()
        if any(hint in lowered for hint in SECRET_KEY_HINTS):
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted


class RealBaseManager:
    """Provide shared ORM query helpers for one model class."""

    def __init__(self, cls):
        self.cls = cls
        self.logger = get_logger(cls.__name__, AIRUNNER_LOG_LEVEL)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
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
                        "Error applying eager load for "
                        "relationship %s: %s",
                        relationship,
                        exc,
                    )
        return query

    @staticmethod
    def _bounded_limit(limit: Optional[int]) -> Optional[int]:
        """Return an effective row limit, or None for unbounded.

        ``None`` preserves the historical unbounded behavior; an explicit
        value is clamped into [1, DEFAULT_LIST_LIMIT * 10].
        """
        if limit is None:
            return None
        try:
            return max(1, min(int(limit), DEFAULT_LIST_LIMIT * 10))
        except (TypeError, ValueError):
            return DEFAULT_LIST_LIMIT

    def _apply_paging(
        self,
        query: Query,
        limit: Optional[int],
        offset: Optional[int],
    ) -> Query:
        """Apply optional limit/offset paging to one list query."""
        bounded = self._bounded_limit(limit)
        if bounded is not None:
            query = query.limit(bounded)
        if offset is not None:
            try:
                query = query.offset(max(0, int(offset)))
            except (TypeError, ValueError):
                pass
        return query

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------
    def get(
        self, pk, eager_load: Optional[List[str]] = None
    ) -> Optional[_T]:
        """Return one row by primary key, or None."""
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
        """Return one live ORM instance (attached) for updates."""
        with session_scope() as session:
            try:
                query = session.query(self.cls)
                query = self._apply_eager_load(query, eager_load)
                return query.filter(self.cls.id == pk).first()
            except Exception as exc:
                self.logger.error("Error in get_orm(%s): %s", pk, exc)
                return None

    def first(
        self, eager_load: Optional[List[str]] = None
    ) -> Optional[_T]:
        """Return the first row as a dataclass, or None."""
        with session_scope() as session:
            if self.cls.__name__ == "Chatbot" and eager_load is None:
                mapper = inspect(self.cls)
                eager_load = [rel.key for rel in mapper.relationships]
            query = session.query(self.cls)
            query = self._apply_eager_load(query, eager_load)
            result = query.first()
            session.expunge_all()
            return result.to_dataclass() if result else None

    def get_or_create(
        self, defaults: Optional[dict] = None, **kwargs
    ) -> Any:
        """Get one existing record or create and return a new one."""
        with session_scope() as session:
            try:
                if kwargs:
                    result = (
                        session.query(self.cls)
                        .filter_by(**kwargs)
                        .first()
                    )
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
                self.logger.error(
                    "Error in get_or_create(%s): %s",
                    _redacted_kwargs(kwargs),
                    exc,
                )
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
                self.logger.error(
                    "Error in create(%s): %s",
                    _redacted_kwargs(kwargs),
                    exc,
                )
                return None

    def update(self, pk=None, **kwargs) -> bool:
        """Update one record by id and return whether it succeeded."""
        record_id = kwargs.pop("pk", pk)
        if not kwargs or record_id is None:
            return False

        with session_scope() as session:
            try:
                result = (
                    session.query(self.cls)
                    .filter(self.cls.id == record_id)
                    .first()
                )

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
                    _redacted_kwargs(kwargs),
                    exc,
                )
                return False

    def all(
        self,
        eager_load: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[_T]:
        """Return rows converted to dataclasses, with paging."""
        with session_scope() as session:
            try:
                query = session.query(self.cls)
                query = self._apply_eager_load(query, eager_load)
                query = self._apply_paging(query, limit, offset)
                result = query.all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as exc:
                self.logger.error("Error in all(): %s", exc)
                return []

    def filter_by(
        self,
        *positional: object,
        eager_load: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs,
    ) -> Optional[List[_T]]:
        """Return rows matching simple equality filters, with paging."""
        if positional:
            raise TypeError(
                "filter_by() takes no positional filters; "
                "use filter() or keyword arguments"
            )
        with session_scope() as session:
            try:
                query = session.query(self.cls).filter_by(**kwargs)
                query = self._apply_eager_load(query, eager_load)
                query = self._apply_paging(query, limit, offset)
                result = query.all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as exc:
                self.logger.error(
                    "Error in filter_by(%s): %s",
                    _redacted_kwargs(kwargs),
                    exc,
                )
                return None

    def filter_first(self, *args) -> Optional[_T]:
        """Return the first row matching arbitrary filters."""
        with session_scope() as session:
            try:
                result = (
                    session.query(self.cls).filter(*args).first()
                )
                session.expunge_all()
                return result.to_dataclass() if result else None
            except Exception as exc:
                self.logger.error(
                    "Error in filter(%s): %s", args, exc
                )
                return None

    def filter(
        self,
        *args,
        eager_load: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Optional[List[_T]]:
        """Return rows matching arbitrary filters, with paging."""
        with session_scope() as session:
            try:
                query = session.query(self.cls).filter(*args)
                query = self._apply_eager_load(query, eager_load)
                query = self._apply_paging(query, limit, offset)
                result = query.all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as exc:
                self.logger.error(
                    "Error in filter(%s): %s", args, exc
                )
                return None

    def filter_by_first(
        self,
        eager_load: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[_T]:
        """Return the first row matching equality filters."""
        with session_scope() as session:
            try:
                query = session.query(self.cls)
                if eager_load:
                    for relationship in eager_load:
                        try:
                            query = query.options(
                                joinedload(
                                    getattr(self.cls, relationship)
                                )
                            )
                        except AttributeError:
                            self.logger.warning(
                                "Class %s does not have "
                                "relationship %s",
                                self.cls.__name__,
                                relationship,
                            )
                result = query.filter_by(**kwargs).first()
                session.expunge_all()
                return result.to_dataclass() if result else None
            except Exception as exc:
                self.logger.error(
                    "Error in filter_by(%s): %s",
                    _redacted_kwargs(kwargs),
                    exc,
                )
                return None

    def order_by(self, *args) -> Optional[Query]:
        """Return an ordered query (rarely used directly)."""
        with session_scope() as session:
            try:
                result = session.query(self.cls).order_by(*args)
                session.expunge_all()
                return result
            except Exception as exc:
                self.logger.error(
                    "Error in order_by(%s): %s", args, exc
                )
                return None

    def options(self, *args) -> Optional[Query]:
        """Return a query with loader options applied."""
        with session_scope() as session:
            try:
                result = session.query(self.cls).options(*args)
                session.expunge_all()
                return result
            except Exception as exc:
                self.logger.error(
                    "Error in options(%s): %s", args, exc
                )
                return None

    def delete(self, pk=None, **kwargs) -> bool:
        """Delete one row by primary key or by filter criteria."""
        with session_scope() as session:
            try:
                if pk is not None:
                    obj = (
                        session.query(self.cls)
                        .filter(self.cls.id == pk)
                        .first()
                    )
                    if obj:
                        session.delete(obj)
                        session.commit()
                        return True
                    return False
                if kwargs:
                    query = session.query(self.cls).filter_by(**kwargs)
                    return self._guarded_bulk_delete(session, query) >= 0
                return False
            except Exception as exc:
                self.logger.error(
                    "Error in delete(%s, %s): %s",
                    pk,
                    _redacted_kwargs(kwargs),
                    exc,
                )
                return False

    def _guarded_bulk_delete(self, session, query) -> int:
        """Delete via query, refusing removals above the row cap.

        Returns:
            Rows removed, or -1 when the row cap refused the delete.
        """
        matched = query.count()
        if matched > MAX_BULK_DELETE_ROWS:
            self.logger.error(
                "Refusing bulk delete of %d %s rows (cap %d); "
                "narrow the filter",
                matched,
                self.cls.__name__,
                MAX_BULK_DELETE_ROWS,
            )
            session.rollback()
            return -1
        result = query.delete()
        session.commit()
        return result

    def delete_all(self, confirm: bool = False) -> int:
        """Delete all rows and return the count removed.

        Args:
            confirm: Must be True; deleting a whole table without an
                explicit opt-in is refused with a -1 return.
        """
        if not confirm:
            self.logger.error(
                "Refusing unconfirmed delete_all() on %s; "
                "pass confirm=True",
                self.cls.__name__,
            )
            return -1
        with session_scope() as session:
            try:
                query = session.query(self.cls)
                return max(self._guarded_bulk_delete(session, query), 0)
            except Exception as exc:
                self.logger.error("Error in delete(): %s", exc)
                return 0

    def delete_by(self, **kwargs) -> bool:
        """Delete rows matching equality filters."""
        if not kwargs:
            self.logger.error(
                "Refusing delete_by() with empty filter on %s",
                self.cls.__name__,
            )
            return False
        with session_scope() as session:
            try:
                query = session.query(self.cls).filter_by(**kwargs)
                return self._guarded_bulk_delete(session, query) >= 0
            except Exception as exc:
                self.logger.error(
                    "Error in delete_by(%s): %s",
                    _redacted_kwargs(kwargs),
                    exc,
                )
                return False

    # ------------------------------------------------------------------
    # Instance-level operations (called by BaseModel.save/delete)
    # ------------------------------------------------------------------
    def save(self, instance) -> bool:
        """Persist an existing ORM instance."""
        with session_scope() as session:
            try:
                session.add(instance)
                session.commit()
                session.refresh(instance)
                return True
            except Exception as exc:
                self.logger.error("Error in save(): %s", exc)
                return False

    def delete_instance(self, instance) -> bool:
        """Delete an ORM instance from the database."""
        with session_scope() as session:
            try:
                session.delete(instance)
                session.commit()
                return True
            except Exception as exc:
                self.logger.error("Error in delete(): %s", exc)
                return False


__all__ = [
    "DEFAULT_LIST_LIMIT",
    "MAX_BULK_DELETE_ROWS",
    "RealBaseManager",
    "SECRET_KEY_HINTS",
]
