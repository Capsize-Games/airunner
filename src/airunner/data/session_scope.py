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
def generator_scope():
    from airunner.data.models import GeneratorSetting
    with session_scope() as session:
        generator = session.query(GeneratorSetting).options(joinedload('*')).first()
        yield generator

@contextmanager
def active_grid_settings_scope():
    from airunner.data.models import ActiveGridSettings
    with session_scope() as session:
        active_grid_settings = session.query(ActiveGridSettings).options(joinedload('*')).first()
        yield active_grid_settings

@contextmanager
def path_settings_scope():
    from airunner.data.models import PathSettings
    with session_scope() as session:
        path_settings = session.query(PathSettings).options(joinedload('*')).first()
        yield path_settings


@contextmanager
def standard_image_widget_settings_scope():
    from airunner.data.models import StandardImageWidgetSettings
    with session_scope() as session:
        standard_image_widget_settings = session.query(StandardImageWidgetSettings).options(joinedload('*')).first()
        yield standard_image_widget_settings

@contextmanager
def generator_settings_scope():
    from airunner.data.models import GeneratorSetting
    with session_scope() as session:
        generator_settings = session.query(GeneratorSetting).options(joinedload('*')).first()
        yield generator_settings


@contextmanager
def models_scope():
    from airunner.data.models import AIModel
    with session_scope() as session:
        models = session.query(AIModel).all()
        yield models


@contextmanager
def llm_generator_scope():
    from airunner.data.models import LLMGenerator
    with session_scope() as session:
        llm_generator = session.query(LLMGenerator).options(joinedload('*')).first()
        yield llm_generator

@contextmanager
def llm_generator_settings_scope():
    from airunner.data.models import LLMGeneratorSetting
    with session_scope() as session:
        llm_generator = session.query(LLMGeneratorSetting).options(joinedload('*')).first()
        yield llm_generator

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

@contextmanager
def metadata_settings_scope():
    from airunner.data.models import MetadataSettings
    with session_scope() as session:
        metadata_settings = session.query(MetadataSettings).options(joinedload('*')).first()
        yield metadata_settings