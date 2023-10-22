from PyQt6.QtCore import QObject, pyqtSignal

from airunner.aihandler.qtvar import StringVar, IntVar, BooleanVar, FloatVar, DictVar
from airunner.data.db import session
from airunner.data.models import LLMGenerator, Settings, GeneratorSetting, AIModel, Pipeline, ControlnetModel, ImageFilter, Prompt, \
    SavedPrompt, PromptCategory, PromptVariable, PromptVariableCategory, PromptVariableCategoryWeight
from airunner.utils import save_session
from airunner.aihandler.logger import Logger as logger

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


class SettingsSignal(QObject):
    _instances = {}
    changed_signal = pyqtSignal(str, object, object)

    def __new__(cls):
        if cls not in cls._instances:
            cls._instances[cls] = super(SettingsSignal, cls).__new__(cls)
        return cls._instances[cls]


class SettingsManager(QObject):
    saved_signal = pyqtSignal()
    changed_signal = SettingsSignal().changed_signal

    @property
    def prompts(self):
        """
        Return Prompt objects from the database
        :return:
        """
        return session.query(SavedPrompt).all()

    def create_saved_prompt(self, prompt, negative_prompt):
        if prompt == "" and negative_prompt == "":
            return

        saved_prompt = SavedPrompt(
            prompt=prompt,
            negative_prompt=negative_prompt
        )
        session.add(saved_prompt)
        if save_session(session):
            self.changed_signal.emit("saved_prompt", saved_prompt, self)

    def delete_prompt(self, saved_prompt):
        session.delete(saved_prompt)
        session.commit()
        self.save_and_emit("saved_prompt", saved_prompt)
        self.changed_signal.emit("saved_prompt", saved_prompt, self)

    def save_and_emit(self, key, value):
        self.save()
        self.changed_signal.emit(key, value, self)

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
        try:
            return session.query(Pipeline).filter_by(
                category=category,
                pipeline_action=pipeline_action,
                version=version
            ).first().classname
        except AttributeError:
            logger.error(f"Unable to find pipeline classname for {pipeline_action} {version} {category}")
            return None

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
        generator = self.find_generator(self.generator_section, self.generator_name)
        if not generator:
            logger.error(f"Unable to find generator {self.generator_section} {self.generator_name}")
        return generator
    
    @property
    def llm_generator_setting(self):
        llm_generator = session.query(LLMGenerator).first()
        return llm_generator.generator_settings[0]


    def find_generator(self, generator_section, generator_name):
        # using sqlalchemy, query the document.settings.generator_settings column
        # and find any with GeneratorSettings.section == self.generator_section and GeneratorSettings.generator_name == self.generator_name
        # return the first result
        generator_settings = session.query(GeneratorSetting).filter_by(
            section=generator_section,
            generator_name=generator_name
        ).join(Settings).first()
        if generator_settings is None:
            if not generator_section or generator_section == "" or not generator_name or generator_name == "":
                return None
            generator_settings = GeneratorSetting(
                section=generator_section,
                generator_name=generator_name,
                settings_id=document.settings.id,
            )
            session.add(generator_settings)
            session.commit()
        return generator_settings

    def __init__(self, app=None, *args, **kwargs):
        global _app, document
        self.can_save = True

        if app:
            _app = app
            document = _app.document
        else:
            from airunner.data.db import session
            from airunner.data.models import Document
            document = session.query(Document).first()

        super().__init__(*args, **kwargs)

    _generator_section = None
    _generator_name = None

    @property
    def generator_section(self):
        if self._generator_section:
            return self._generator_section
        return getattr(self, f"current_section_{self.current_tab}")

    @property
    def generator_name(self):
        if self._generator_name:
            return self._generator_name
        return self.current_tab

    @generator_section.setter
    def generator_section(self, value):
        self._generator_section = value

    @generator_name.setter
    def generator_name(self, value):
        self._generator_name = value

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
        if name in ["can_save", "generator_section", "generator_name", "_generator_section", "_generator_name"]:
            super().__setattr__(name, value)
            return
        if document and hasattr(document.settings, name):
            setattr(document.settings, name, value)
            self.changed_signal.emit(name, value, self)

    def set_value(self, key, value):
        keys = key.split('.')
        obj = self
        for k in keys[:-1]:  # Traverse till second last key
            obj = getattr(self, k)
        setattr(obj, keys[-1], value)
        self.save()
        self.changed_signal.emit(key, value, self)

    def get_value(self, key):
        keys = key.split('.')
        obj = self
        for k in keys:
            obj = getattr(obj, k)
        return obj

    @property
    def current_tab_action(self):
        current_tab = self.current_tab
        if current_tab == "stablediffusion":
            return self.current_section_stablediffusion
        elif current_tab == "kandinsky":
            return self.current_section_kandinsky
        else:
            return self.current_section_shapegif

    @property
    def prompt_builder_prompts(self):
        return session.query(Prompt).all()

    @property
    def prompt_categories(self):
        return session.query(PromptCategory).all()

    def variables_by_category(self, category_name):
        variable_category = session.query(PromptVariableCategory).filter_by(name=category_name).first()
        return session.query(PromptVariable).filter_by(variable_category=variable_category).all()

    def prompts_by_category(self, category_name):
        category = session.query(PromptCategory).filter_by(name=category_name).first()
        return session.query(Prompt).filter_by(category=category).all()

    def variable_weights_by_category(self, category, variable_name):
        variable = session.query(PromptVariable).filter_by(value=variable_name).first()
        return session.query(PromptVariableCategoryWeight).filter_by(
            prompt_category_id=variable.prompt_category_id,
            variable_category_id=variable.variable_category_id
        ).first()

    def save(self):
        session.commit()
