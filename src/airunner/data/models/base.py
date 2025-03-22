from typing import Optional, List, TypeVar, Any
import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Query

import traceback

from airunner.data.session_manager import session_scope

_T = TypeVar("_T", bound=Any)

Base = declarative_base()
logger = logging.getLogger(__name__)


class BaseManager:
    def __init__(self, cls):
        self.cls = cls

    def get(self, pk) -> Optional[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(self.cls.id == pk).first()
                logger.debug(f"Query result for get({pk}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in get({pk}): {e}")
                return None

    def first(self) -> Optional[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).first()
                logger.debug(f"Query result for first(): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in first(): {e}")
                return None

    def all(self) -> List[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).all()
                logger.debug(f"Query result for all(): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in all(): {e}")
                return []

    def filter_by(self, **kwargs) -> Optional[List[_T]]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).all()
                logger.debug(f"Query result for filter_by({kwargs}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in filter_by({kwargs}): {e}")
                return None
    
    def filter_first(self, *args) -> Optional[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args).first()
                logger.debug(f"Query result for filter({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in filter({args}): {e}")
                return None

    def filter(self, *args) -> Optional[List[_T]]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args).all()
                logger.debug(f"Query result for filter({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in filter({args}): {e}")
                return None

    def filter_by_first(self, **kwargs) -> Optional[_T]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).first()
                logger.debug(f"Query result for filter_by({kwargs}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in filter_by({kwargs}): {e}")
                return None
    
    def order_by(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).order_by(*args)
                logger.debug(f"Query result for order_by({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in order_by({args}): {e}")
                return None
    
    def options(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).options(*args)
                logger.debug(f"Query result for options({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in options({args}): {e}")
                return None

    def delete_all(self) -> int:
        with session_scope() as session:
            try:
                result = session.query(self.cls).delete()
                session.commit()
                logger.debug(f"Deleted {result} {self.cls.__name__} objects")
                return result
            except Exception as e:
                logger.error(f"Error in delete(): {e}")
                return 0

    def delete_by(self, **kwargs) -> bool:
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs).delete()
                session.commit()
                logger.debug(f"Deleted {result} {self.cls.__name__} objects")
                return result
            except Exception as e:
                logger.error(f"Error in delete_by({kwargs}): {e}")
                return False

    def delete(self, pk=None, **kwargs) -> bool:
        with session_scope() as session:
            try:
                if pk:
                    obj = session.query(self.cls).filter(self.cls.id == pk).first()
                    if obj:
                        session.delete(obj)
                        session.commit()
                        logger.debug(f"Deleted {self.cls.__name__} with id {pk}")
                        return True
                    else:
                        logger.debug(f"No {self.cls.__name__} found with id {pk}")
                        return False
                elif kwargs:
                    result = session.query(self.cls).filter_by(**kwargs).delete()
                    session.commit()
                    logger.debug(f"Deleted {result} {self.cls.__name__} objects")
                    return result
                else:
                    logger.debug("No arguments provided to delete()")
                    return False
            except Exception as e:
                logger.error(f"Error in delete({pk}): {e}")
                return False
    
    def update(self, pk, **kwargs) -> bool:
        with session_scope() as session:
            try:
                obj = session.query(self.cls).filter(self.cls.id == pk).first()
                if obj:
                    for key, value in kwargs.items():
                        setattr(obj, key, value)
                    session.commit()
                    logger.debug(f"Updated {self.cls.__name__} with id {pk}")
                    return True
                else:
                    logger.debug(f"No {self.cls.__name__} found with id {pk}")
                    return False
            except Exception as e:
                logger.error(f"Error in update({pk}, {kwargs}): {e}")
                return False
    
    def merge(self, obj) -> bool:
        with session_scope() as session:
            try:
                session.merge(obj)
                session.commit()
                logger.debug(f"Merged {self.cls.__name__}")
                return True
            except Exception as e:
                logger.error(f"Error in merge(): {e}")
                return False
    
    def distinct(self, *args) -> Optional[Query]:
        with session_scope() as session:
            try:
                result = session.query(self.cls).distinct(*args)
                logger.debug(f"Query result for distinct({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in distinct({args}): {e}")
                return None
    
    def create(self, *args, **kwargs) -> Optional[_T]:
        obj = None
        with session_scope() as session:
            try:
                obj = self.cls(*args, **kwargs)
                session.add(obj)
                session.commit()
                logger.debug(f"Created {self.cls.__name__}")
            except Exception as e:
                logger.error(f"Error in create({args}, {kwargs}): {e}")
            finally:
                session.expunge(obj)
        return obj


class BaseModel(Base):
    __abstract__ = True

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

    def to_dict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
