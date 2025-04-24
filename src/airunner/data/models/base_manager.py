from typing import Optional, List, TypeVar, Any
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Query, joinedload, subqueryload

from airunner.data.session_manager import session_scope
from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL

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
                    # Use subqueryload instead of joinedload
                    query = query.options(
                        subqueryload(getattr(self.cls, relationship))
                    )
                    self.logger.debug(
                        f"Applied eager load for relationship: {relationship}"
                    )
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
            try:
                query = session.query(self.cls)
                query = self._apply_eager_load(query, eager_load)
                result = query.filter(self.cls.id == pk).first()
                session.expunge_all()
                self.logger.debug(f"Query result for get({pk}): {result}")
                return result
            except Exception as e:
                self.logger.error(f"Error in get({pk}): {e}")
                return None

    def first(self, eager_load: Optional[List[str]] = None) -> Optional[_T]:
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
                result = query.first()
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in first(): {e}")
                return None

    def all(self) -> List[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).all()
                self.logger.debug(f"Query result for all(): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in all(): {e}")
                return []

    def filter_by(self, **kwargs) -> Optional[List[_T]]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).all()
                self.logger.debug(
                    f"Query result for filter_by({kwargs}): {result}"
                )
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in filter_by({kwargs}): {e}")
                return None

    def filter_first(self, *args) -> Optional[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args).first()
                self.logger.debug(f"Query result for filter({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in filter({args}): {e}")
                return None

    def filter(self, *args) -> Optional[List[_T]]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args).all()
                self.logger.debug(f"Query result for filter({args}): {result}")
                session.expunge_all()
                return result
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
                self.logger.debug(
                    f"Query result for filter_by({kwargs}): {result}"
                )
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in filter_by({kwargs}): {e}")
                return None

    def order_by(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).order_by(*args)
                self.logger.debug(
                    f"Query result for order_by({args}): {result}"
                )
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in order_by({args}): {e}")
                return None

    def options(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).options(*args)
                self.logger.debug(
                    f"Query result for options({args}): {result}"
                )
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
                self.logger.debug(
                    f"Deleted {result} {self.cls.__name__} objects"
                )
                return result
            except Exception as e:
                self.logger.error(f"Error in delete(): {e}")
                return 0

    def delete_by(self, **kwargs) -> bool:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).delete()
                session.commit()
                self.logger.debug(
                    f"Deleted {result} {self.cls.__name__} objects"
                )
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
                        self.logger.debug(
                            f"Deleted {self.cls.__name__} with id {pk}"
                        )
                        return True
                    else:
                        self.logger.debug(
                            f"No {self.cls.__name__} found with id {pk}"
                        )
                        return False
                elif kwargs:
                    result = (
                        session.query(self.cls).filter_by(**kwargs).delete()
                    )
                    session.commit()
                    self.logger.debug(
                        f"Deleted {result} {self.cls.__name__} objects"
                    )
                    return result
                else:
                    self.logger.debug("No arguments provided to delete()")
                    return False
            except Exception as e:
                self.logger.error(f"Error in delete({pk}): {e}")
                return False

    def update(self, pk, **kwargs) -> bool:
        with session_scope() as session:
            try:
                obj = session.query(self.cls).filter(self.cls.id == pk).first()
                if obj:
                    for key, value in kwargs.items():
                        setattr(obj, key, value)
                    session.commit()
                    self.logger.debug(
                        f"Updated {self.cls.__name__} with id {pk}"
                    )
                    return True
                else:
                    self.logger.debug(
                        f"No {self.cls.__name__} found with id {pk}"
                    )
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
                    self.logger.debug(
                        f"No {self.cls.__name__} found with {kwargs}"
                    )
                    return False
            except Exception as e:
                self.logger.error(f"Error in update: {e}")
                return False

    def merge(self, obj) -> bool:
        with session_scope() as session:
            try:
                session.merge(obj)
                session.commit()
                self.logger.debug(f"Merged {self.cls.__name__}")
                return True
            except Exception as e:
                self.logger.error(f"Error in merge(): {e}")
                return False

    def distinct(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).distinct(*args)
                self.logger.debug(
                    f"Query result for distinct({args}): {result}"
                )
                session.expunge_all()
                return result
            except Exception as e:
                self.logger.error(f"Error in distinct({args}): {e}")
                return None

    def create(self, *args, **kwargs) -> Optional[_T]:
        obj = None
        with session_scope() as session:
            try:
                obj = self.cls(*args, **kwargs)
                session.add(obj)
                session.commit()
                self.logger.debug(f"Created {self.cls.__name__}")
                return obj.to_dataclass()
            except Exception as e:
                self.logger.error(f"Error in create({args}, {kwargs}): {e}")
                return
        self.self.logger.error("Something went wrong")
