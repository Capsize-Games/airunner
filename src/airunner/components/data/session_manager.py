from contextlib import contextmanager
from sqlalchemy.orm import scoped_session, sessionmaker
from airunner.settings import AIRUNNER_DB_URL
from sqlalchemy import create_engine


engine = create_engine(AIRUNNER_DB_URL)
Session = scoped_session(sessionmaker(bind=engine))


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
