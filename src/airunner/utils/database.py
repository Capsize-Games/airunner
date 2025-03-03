from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from airunner.settings import DB_PATH, DB_URL


class Database:
    engine = create_engine(DB_URL)
    Session = scoped_session(sessionmaker(bind=engine))

    @classmethod
    @contextmanager
    def session_scope(cls):
        """Provide a transactional scope around a series of operations."""
        session = cls.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            cls.Session.remove()

    @classmethod
    def with_session(cls, func):
        """Decorator that provides a session to the method."""
        def wrapper(*args, **kwargs):
            with cls.session_scope() as session:
                return func(*args, session=session, **kwargs)
        return wrapper
