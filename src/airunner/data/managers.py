from contextlib import contextmanager
from typing import Iterator
from sqlalchemy.orm import joinedload
from PyQt6.QtCore import QObject, pyqtSignal
from airunner.utils import Logger

from airunner.data.session_scope import (
    models_scope,
    session_scope,
)


class Modelmanager:
    logger = Logger(prefix="Modelmanager")
    def __init__(self, scope_function):
        self.scope_function = scope_function

    def get_property(self, name: str) -> str:
        try:
            with self.scope_function() as object:
                try:
                    value = getattr(object, name)
                except AttributeError:
                    import traceback 
                    traceback.print_exc()
                    #value = object.default  # Use the default value of the object in scope
                    value = None
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.logger.error(f"Error while getting property {name}: {e}")
            value = None  # Return None if there's an error
        return value

    def get_properties(self, name: str = None) -> Iterator[str]:
        try:
            with self.scope_function() as objects:
                for object in objects:
                    if name is None:
                        yield object
                    else:
                        try:
                            value = getattr(object, name)
                        except AttributeError:
                            value = object.default  # Use the default value of the object in scope
                        yield value
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.logger.error(f"Error while getting property {name}: {e}")
            yield None  # Yield None if there's an error

    def __getattr__(self, name):
        return self.get_property(name)


class SettingsManager(QObject):
    logger = Logger(prefix="SettingsManager")
    _instance = None  # Keep instance reference 
    changed_signal = pyqtSignal(str, object)

    scopes = {
        "models": models_scope,
    }

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = super(SettingsManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    # todo: handle changed_signalgrid_settings
    def __init__(self):
        super().__init__()
        self.models = Modelmanager(models_scope)
    
    @contextmanager
    def image_filters_scope(self):
        from airunner.data.models import ImageFilter
        with session_scope() as session:
            image_filters = session.query(ImageFilter).options(joinedload('*')).all()
            yield image_filters
    
    @contextmanager
    def image_filter_by_name(self, filter_name):
        from airunner.data.models import ImageFilter
        with session_scope() as session:
            image_filter = session.query(ImageFilter).options(joinedload('*')).filter_by(name=filter_name).first()
            yield image_filter

    @contextmanager
    def available_pipeline_by_section(self, pipeline_action, version, category):
        from airunner.data.models import Pipeline
        with session_scope() as session:
            pipelines = session.query(Pipeline).filter_by(
                category=category,
                pipeline_action=pipeline_action,
                version=version
            ).first()
            yield pipelines
    
    @contextmanager
    def model_by_name(self, name):
        from airunner.data.models import AIModel
        with session_scope() as session:
            model = session.query(AIModel).options(joinedload('*')).filter(
                AIModel.name.like(f"%{name}%") if name != "" else True).first()
            yield model

    @contextmanager
    def brushes(self):
        from airunner.data.models import Brush
        with session_scope() as session:
            brushes = session.query(Brush).options(joinedload('*')).all()
            yield brushes
    
    @contextmanager
    def loras(self, search_filter=None):
        from airunner.data.models import Lora
        with session_scope() as session:
            if search_filter:
                loras = session.query(Lora).options(joinedload('*')).filter(
                    Lora.name.like(f"%{self.search_filter}%") if self.search_filter != "" else True).all()
            else:
                loras = session.query(Lora).options(joinedload('*')).all()
            yield loras            

    @contextmanager
    def document(self):
        from airunner.data.models import Document
        with session_scope() as session:
            document = session.query(Document).options(joinedload('*')).first()
            yield document

    @contextmanager
    def models_by_pipeline_action(self, pipeline_action):
        with session_scope() as session:
            from airunner.data.models import AIModel
            models = session.query(AIModel).options(joinedload('*')).all()
            models.filter_by(pipeline_action=pipeline_action).all()
            yield models
    
    def get_value(self, key):
        keys = key.split('.')
        obj = self
        for k in keys:
            try:
                obj = getattr(obj, k)
            except AttributeError:
                self.logger.error(f"Unable to find key {key}")
                return None
        return obj
    
    def set_value(self, key, value):
        keys = key.split('.')
        obj = self
        for k in keys[:-1]:  # Traverse till second last key
            if k in self.scopes:
                with self.scopes[k]() as object:
                    obj = object
                    setattr(obj, keys[-1], value)

        self.changed_signal.emit(key, value)