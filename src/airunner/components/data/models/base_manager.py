from typing import Optional, List, TypeVar, Any
from sqlalchemy.orm import Query, joinedload, subqueryload, declarative_base
from sqlalchemy.inspection import inspect

from airunner.components.data.session_manager import session_scope
from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL
import traceback

_T = TypeVar("_T", bound=Any)

Base = declarative_base()


class BaseManager:
    def __init__(self, cls):
        self.cls = cls
        self.logger = get_logger(cls.__name__, AIRUNNER_LOG_LEVEL)

    def _apply_eager_load(
        self, query: Query, eager_load: Optional[List[str]]
    ) -> Query:
        if eager_load:
            for relationship in eager_load:
                try:
                    # Only apply subqueryload to actual relationships
                    rel_attr = getattr(self.cls, relationship)
                    if hasattr(rel_attr, "property") and hasattr(
                        rel_attr.property, "direction"
                    ):
                        query = query.options(subqueryload(rel_attr))
                except AttributeError:
                    self.logger.warning(
                        f"Class {self.cls.__name__} does not have relationship {relationship}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error applying eager load for relationship {relationship}: {e}"
                    )
        return query

    def get(self, pk, eager_load: Optional[List[str]] = None) -> Optional[_T]:
        with session_scope() as session:
            # Only eager load relationships for Chatbot
            if self.cls.__name__ == "Chatbot" and eager_load is None:
                mapper = inspect(self.cls)
                eager_load = [rel.key for rel in mapper.relationships]
            query = session.query(self.cls)
            query = self._apply_eager_load(query, eager_load)
            result = query.filter(self.cls.id == pk).first()
            session.expunge_all()
            return result.to_dataclass() if result else None

    def get_orm(
        self, pk, eager_load: Optional[List[str]] = None
    ) -> Optional[Any]:
        """
        Return a live ORM instance (not a dataclass) for update/delete/session operations.
        """
        with session_scope() as session:
            try:
                query = session.query(self.cls)
                query = self._apply_eager_load(query, eager_load)
                result = query.filter(self.cls.id == pk).first()
                return result
            except Exception as e:
                self.logger.error(f"Error in get_orm({pk}): {e}")
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

    def all(self) -> List[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as e:
                self.logger.error(f"Error in all(): {e}")
                return []

    def filter_by(self, **kwargs) -> Optional[List[_T]]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as e:
                self.logger.error(f"Error in filter_by({kwargs}): {e}")
                return None

    def filter_first(self, *args) -> Optional[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args).first()
                session.expunge_all()
                return result.to_dataclass() if result else None
            except Exception as e:
                self.logger.error(f"Error in filter({args}): {e}")
                return None

    def filter(self, *args) -> Optional[List[_T]]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args).all()
                session.expunge_all()
                return [obj.to_dataclass() for obj in result]
            except Exception as e:
                self.logger.error(f"Error in filter({args}): {e}")
                return None

    def filter_by_first(
        self, eager_load: Optional[List[str]] = None, **kwargs
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
                                (
                                    f"Class {self.cls.__name__} does "
                                    "not have relationship {relationship}"
                                )
                            )
                            pass
                result = query.filter_by(**kwargs).first()
                session.expunge_all()
                return result.to_dataclass() if result else None
            except Exception as e:
                self.logger.error(f"Error in filter_by({kwargs}): {e}")
                return None

    def order_by(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).order_by(*args)
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in order_by({args}): {e}")
                return None

    def options(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).options(*args)
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in options({args}): {e}")
                return None

    def delete_all(self) -> int:
        with session_scope() as session:
            try:
                result = session.query(self.cls).delete()
                session.commit()
                return result
            except Exception as e:
                self.logger.error(f"Error in delete(): {e}")
                return 0

    def delete_by(self, **kwargs) -> bool:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).delete()
                session.commit()
                return result
            except Exception as e:
                self.logger.error(f"Error in delete_by({kwargs}): {e}")
                return False

    def delete(self, pk=None, **kwargs) -> bool:
        with session_scope() as session:
            try:
                if pk:
                    obj = (
                        session.query(self.cls)
                        .filter(self.cls.id == pk)
                        .first()
                    )
                    if obj:
                        session.delete(obj)
                        session.commit()
                        return True
                    else:
                        return False
                elif kwargs:
                    result = (
                        session.query(self.cls).filter_by(**kwargs).delete()
                    )
                    session.commit()
                    return result
                else:
                    return False
            except Exception as e:
                self.logger.error(f"Error in delete({pk}): {e}")
                return False

    def update(self, pk, **kwargs) -> bool:
        with session_scope() as session:
            try:
                obj = session.query(self.cls).filter(self.cls.id == pk).first()
                # Debug: log GeneratorSettings updates to help trace unexpected overwrites
                try:
                    if (
                        getattr(self.cls, "__name__", "")
                        == "GeneratorSettings"
                    ):
                        self.logger.debug(
                            "GeneratorSettings.update called: pk=%s kwargs=%s",
                            pk,
                            kwargs,
                        )
                        self.logger.debug(
                            "Stack for GeneratorSettings.update:\n%s",
                            "".join(traceback.format_stack()),
                        )
                except Exception:
                    pass
                if obj:
                    for key, value in kwargs.items():
                        setattr(obj, key, value)
                    session.commit()
                    return True
                else:
                    return False
            except Exception as e:
                self.logger.error(f"Error in update({pk}, {kwargs}): {e}")
                return False

    def update_by(self, filter: dict, **kwargs) -> bool:
        with session_scope() as session:
            try:
                objs = session.query(self.cls).filter_by(**filter)
                if objs.count() > 0:
                    for obj in objs:
                        for key, value in kwargs.items():
                            setattr(obj, key, value)
                            session.commit()
                    return True
                else:
                    return False
            except Exception as e:
                self.logger.error(f"Error in update: {e}")
                return False

    def merge(self, obj) -> bool:
        with session_scope() as session:
            try:
                session.merge(obj)
                session.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error in merge(): {e}")
                return False

    def distinct(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).distinct(*args)
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in distinct({args}): {e}")
                return None

    def create(self, *args, **kwargs) -> Optional[_T]:
        """Create a new instance of the managed class and return its dataclass representation.

        Args:
            *args: Positional arguments for the class constructor.
            **kwargs: Keyword arguments for the class constructor.

        Returns:
            Optional[_T]: The created object as a dataclass, or None if creation failed.
        """
        obj = None
        with session_scope() as session:
            try:
                obj = self.cls(*args, **kwargs)
                session.add(obj)
                session.commit()
                return obj.to_dataclass()
            except Exception as e:
                self.logger.error(f"Error in create({args}, {kwargs}): {e}")
                return None
