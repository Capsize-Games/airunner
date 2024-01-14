from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from airunner.settings import SQLITE_DB_PATH

engine = create_engine(f'sqlite:///{SQLITE_DB_PATH}')
Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except IntegrityError as e:
        if 'UNIQUE constraint failed' in str(e):
            session.rollback()
            pass  # skip unique constraint errors
        else:
            session.rollback()
            raise  # re-raise other IntegrityErrors
    except:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def models_scope():
    from airunner.data.models import AIModel
    with session_scope() as session:
        models = session.query(AIModel).all()
        yield models

@contextmanager
def canvas_settings_scope():
    from airunner.data.models import CanvasSettings
    with session_scope() as session:
        canvas_settings = session.query(CanvasSettings).options(joinedload('*')).first()
        yield canvas_settings

@contextmanager
def memory_settings_scope():
    from airunner.data.models import MemorySettings
    with session_scope() as session:
        memory_settings = session.query(MemorySettings).options(joinedload('*')).first()
        yield memory_settings