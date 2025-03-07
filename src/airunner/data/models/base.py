import logging
from sqlalchemy.ext.declarative import declarative_base
from airunner.data.session_manager import session_scope

Base = declarative_base()
logger = logging.getLogger(__name__)

class BaseManager:
    def __init__(self, cls):
        self.cls = cls

    def get(self, pk):
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(self.cls.id == pk).first()
                logger.debug(f"Query result for get({pk}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in get({pk}): {e}")
                return None

    def first(self):
        with session_scope() as session:
            try:
                result = session.query(self.cls).first()
                logger.debug(f"Query result for first(): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in first(): {e}")
                return None

    def all(self):
        with session_scope() as session:
            try:
                result = session.query(self.cls).all()
                logger.debug(f"Query result for all(): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in all(): {e}")
                return []

    def filter_by(self, **kwargs):
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter_by(**kwargs)
                logger.debug(f"Query result for filter_by({kwargs}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in filter_by({kwargs}): {e}")
                return []
    
    def filter(self, *args):
        with session_scope() as session:
            try:
                result = session.query(self.cls).filter(*args)
                logger.debug(f"Query result for filter({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in filter({args}): {e}")
                return []
    
    def order_by(self, *args):
        with session_scope() as session:
            try:
                result = session.query(self.cls).order_by(*args)
                logger.debug(f"Query result for order_by({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in order_by({args}): {e}")
                return []
    
    def options(self, *args):
        with session_scope() as session:
            try:
                result = session.query(self.cls).options(*args)
                logger.debug(f"Query result for options({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in options({args}): {e}")
                return []

    def delete_all(self):
        with session_scope() as session:
            try:
                result = session.query(self.cls).delete()
                session.commit()
                logger.debug(f"Deleted {result} {self.cls.__name__} objects")
                return result
            except Exception as e:
                logger.error(f"Error in delete(): {e}")
                return 0

    def delete(self, pk=None, **kwargs):
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
    
    def update(self, pk, **kwargs):
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
    
    def merge(self, obj):
        with session_scope() as session:
            try:
                session.merge(obj)
                session.commit()
                logger.debug(f"Merged {self.cls.__name__}")
                return True
            except Exception as e:
                logger.error(f"Error in merge(): {e}")
                return False
    
    def distinct(self, *args):
        with session_scope() as session:
            try:
                result = session.query(self.cls).distinct(*args)
                logger.debug(f"Query result for distinct({args}): {result}")
                session.expunge_all()
                return result
            except Exception as e:
                logger.error(f"Error in distinct({args}): {e}")
                return []


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
                logger.debug(f"Saved {self.cls}")
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