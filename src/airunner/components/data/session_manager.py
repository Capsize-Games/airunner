from contextlib import contextmanager
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine


# Lazy-initialized globals
_engine = None
_Session = None


def _get_engine():
    """Get or create the SQLAlchemy engine.

    Lazy initialization ensures the engine uses the correct database URL
    from environment variables, even if they are set after module import.
    This is critical for testing where AIRUNNER_DATABASE_URL is set by
    pytest fixtures.
    """
    global _engine
    if _engine is None:
        # Import here to get current value of AIRUNNER_DB_URL
        from airunner.settings import AIRUNNER_DB_URL

        _engine = create_engine(AIRUNNER_DB_URL)
    return _engine


def _get_session():
    """Get or create the scoped session factory."""
    global _Session
    if _Session is None:
        _Session = scoped_session(sessionmaker(bind=_get_engine()))
    return _Session


def reset_engine():
    """Reset the engine and session.

    Forces recreation of database connections. Useful for tests that change
    the database URL via environment variables.
    """
    global _engine, _Session
    if _Session is not None:
        _Session.remove()
        _Session = None
    if _engine is not None:
        _engine.dispose()
        _engine = None


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    Session = _get_session()
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
