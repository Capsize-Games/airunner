import os
import json

from PyQt6.QtCore import QObject, pyqtSignal
from filelock import FileLock

from airunner.aihandler.database import PromptSettings, ApplicationSettings
from airunner.aihandler.qtvar import Var, StringVar, IntVar, BooleanVar, FloatVar, DictVar
from airunner.data.db import session
from airunner.data.models import Settings, GeneratorSetting, AIModel, Pipeline, ControlnetModel, ImageFilter


class BaseSettingsManager:
    save_disabled = False
    settings = None

    @property
    def default_file_name(self) -> str:
        """
        Override this property to return the default file name.
        This is the file name that will be used to load the default settings.
        Default files are stored in airunner/data
        :return:
        """
        return ""

    @property
    def file_name(self) -> str:
        """
        Override this property to return the file name.
        This is the file name that will be used to store and load the settings
        :return:
        """
        return ""

    def disable_save(self):
        self.save_disabled = True

    def enable_save(self):
        self.save_disabled = False

    def load_default_settings(self):
        path = os.path.join("data", self.default_file_name)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def prepare_data(self, data: dict):
        settings = {}
        if data == {}:
            settings = self.load_default_settings()
        for key, value in data.__dict__.items():
            if isinstance(value, Var):
                settings[key] = value.get()
            elif type(value) in [list, dict, int, float, str, bool]:
                settings[key] = value

        # when settings is empty, then we will fill it with default values
        if settings == {}:
            settings = self.load_default_settings()
        return settings

    def save_file(self, settings):
        home_path = os.path.expanduser("~")
        lock = FileLock(os.path.join(home_path, self.file_name + ".lock"))
        with lock:
            with open(os.path.join(home_path, self.file_name), "w") as f:
                json.dump(settings, f)

    def save_settings(self):
        if self.save_disabled:
            return
        settings = self.prepare_data(self.settings)
        self.save_file(settings)

    def load_settings(self):
        self.disable_save()
        home_path = os.path.expanduser("~")
        if not os.path.exists(os.path.join(home_path, self.file_name)):
            settings = self.load_default_settings()
        else:
            lock = FileLock(os.path.join(home_path, self.file_name + ".lock"))
            with lock:
                with open(os.path.join(home_path, self.file_name), "r") as f:
                    settings = json.load(f)

        for key in settings.keys():
            value = settings[key]
            try:
                self.settings.__dict__[key].set(value)
            except Exception as e:
                self.settings.__dict__[key] = value


document = None
_app = None
variables = {}
variable_types = {
    "VARCHAR": StringVar,
    "INTEGER": IntVar,
    "BOOLEAN": BooleanVar,
    "FLOAT": FloatVar,
    "JSON": DictVar,
}

class GeneratorManager(QObject):
    def __init__(self, settings, *args, **kwargs):
        self.settings = settings
        super().__init__(*args, **kwargs)

    def __getattr__(self, name):
        if document and hasattr(document.settings, name):
            if name not in variables:
                self.create_variable(name)
                variables[name].set(self.get_database_value(name))
            return variables[name]
        return None

    def __setattr__(self, name, value):
        if document and hasattr(document.settings, name):
            if name not in variables:
                self.create_variable(name)
            variables[name].set(value)
            setattr(document.settings, name, value)


class SettingsManager(QObject):
    saved_signal = pyqtSignal()
    changed_signal = pyqtSignal(str, object)
    can_save = True
    section = "stablediffusion"
    tab = "txt2img"

    def available_models_by_category(self, category):
        categories = [category]
        if category in ["img2img", "txt2vid"]:
            categories.append("txt2img")
        return session.query(AIModel).filter(
            AIModel.category.in_(categories),
            AIModel.enabled.is_(True)
        ).all()

    def set_model_enabled(self, key, model, enabled):
        session.query(AIModel).filter_by(
            name=model["name"],
            path=model["path"],
            branch=model["branch"],
            version=model["version"],
            category=model["category"]
        ).update({"enabled": enabled == 2})
        self.save_settings()

    def available_pipeline_by_section(self, pipeline, version, category):
        return session.query(Pipeline).filter_by(
            category=category,
            pipeline_action=pipeline,
            version=version
        ).first()

    def available_model_names(self, pipeline_action, category):
        # returns a list of names of models
        # that match the pipeline_action and category
        names = []
        models = session.query(AIModel).filter_by(
            pipeline_action=pipeline_action,
            category=category,
            enabled=True
        ).all()
        for model in models:
            if model.name not in names:
                names.append(model.name)
        return names

    def add_model(self, model_data):
        model = AIModel(**model_data)
        session.add(model)
        session.commit()

    def delete_model(self, model):
        session.delete(model)
        session.commit()

    def update_model(self, model):
        session.add(model)
        session.commit()

    def get_image_filter(self, name):
        return session.query(ImageFilter).filter_by(name=name).first()

    def get_image_filters(self):
        return session.query(ImageFilter).all()

    @property
    def pipelines(self):
        return session.query(Settings).all()

    @property
    def models(self):
        return session.query(AIModel).filter_by(enabled=True)

    def models_by_pipeline_action(self, pipeline_action):
        return self.models.filter_by(pipeline_action=pipeline_action).all()

    @property
    def controlnet_models(self):
        return session.query(ControlnetModel).filter_by(enabled=True)

    def controlnet_model_by_name(self, name):
        return self.controlnet_models.filter_by(name=name).first()

    @property
    def pipeline_actions(self):
        # return a list of unique pipeline_action properties from the AIModel table and
        actions = []
        for model in self.models.all():
            if model.pipeline_action not in actions:
                actions.append(model.pipeline_action)
        return actions

    @property
    def model_categories(self):
        cateogires = []
        for model in self.models.all():
            if model.category not in cateogires:
                cateogires.append(model.category)
        return cateogires

    def get_pipeline_classname(self, pipeline_action, version, category):
        return session.query(Pipeline).filter_by(
            category=category,
            pipeline_action=pipeline_action,
            version=version
        ).first().classname

    @property
    def model_versions(self):
        versions = []
        for model in self.models.all():
            if model.version not in versions:
                versions.append(model.version)
        return versions

    @property
    def current_prompt_generator_settings(self):
        items = list(filter(lambda x: x.active, self.prompt_generator_settings))
        return items[0] if len(items) > 0 else None

    @property
    def generator(self):
        # using sqlalchemy, query the document.settings.generator_settings column
        # and find any with GeneratorSettings.section == self.section and GeneratorSettings.generator_name == self.tab
        # return the first result
        generator_settings = session.query(GeneratorSetting).filter_by(
            section=self.section,
            generator_name=self.tab
        ).join(Settings).first()
        if generator_settings is None:
            generator_settings = GeneratorSetting(
                section=self.section,
                generator_name=self.tab,
                settings_id=document.settings.id,
            )
            session.add(generator_settings)
            session.commit()
        return generator_settings

    def __init__(self, app=None, *args, **kwargs):
        global _app, document

        if app:
            _app = app
            document = _app.document
        else:
            from airunner.data.db import session
            from airunner.data.models import Document
            document = session.query(Document).first()

        super().__init__(*args, **kwargs)

    def create_variable(self, name):
        var_type = str(getattr(Settings, name).property.columns[0].type)
        variables[name] = variable_types[var_type](_app, getattr(Settings, name).default.arg)

    def get_database_value(self, name):
        return getattr(document.settings, name)

    def __getattr__(self, name):
        if document and hasattr(document.settings, name):
            return getattr(document.settings, name)
        return None

    def __setattr__(self, name, value):
        if document and hasattr(document.settings, name):
            setattr(document.settings, name, value)
            self.changed_signal.emit(name, value)

    def set_value(self, key, value):
        keys = key.split('.')
        obj = self
        for k in keys[:-1]:  # Traverse till second last key
            obj = getattr(self, k)
        setattr(obj, keys[-1], value)
        self.save()
        self.changed_signal.emit(key, value)

    def save(self):
        session.commit()


class PromptManager(BaseSettingsManager):
    _instance = None

    @property
    def file_name(self):
        return "airunner.prompts.json"

    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        cls.app = app
        return cls._instance

    def __init__(self):
        # if not app:
        #     raise Exception("SettingsManager must be initialized with an app")
        self.settings = PromptSettings(app=self)
        self.settings.initialize(self.settings.read())
        try:
            self.load_settings()
        except Exception as e:
            self.save_settings()