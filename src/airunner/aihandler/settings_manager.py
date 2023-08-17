import os
import json

from filelock import FileLock

from airunner.aihandler.database import RunAISettings, PromptSettings, ApplicationSettings
from airunner.aihandler.qtvar import Var


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

        self.enable_save()


class SettingsManager(BaseSettingsManager):
    _instance = None

    @property
    def file_name(self):
        return "airunner.settings.json"

    @property
    def current_tool(self):
        return self.settings.current_tool.get()

    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        cls.app = app
        return cls._instance

    def __init__(self):
        # if not app:
        #     raise Exception("SettingsManager must be initialized with an app")
        self.settings = RunAISettings(app=self)
        self.settings.initialize(self.settings.read())
        try:
            self.load_settings()
        except Exception as e:
            self.save_settings()

    def handle_model_change(self, section, option):
        self.settings.__dict__[f"{section}_model_var"].set(option)

    def handle_scheduler_change(self, section, option):
        self.settings.__dict__[f"{section}_scheduler_var"].set(option)

    def set_kernel_size(self, size):
        self.noise_reduction_amount = int(size)

    def set_colors(self, colors):
        self.total_colors = int(colors)

    def reset_settings_to_default(self):
        self.settings.reset_settings_to_default()
        self.save_settings()


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


class ApplicationData(BaseSettingsManager):
    _instance = None

    @property
    def default_file_name(self):
        return "application.data.json"

    @property
    def file_name(self):
        return "airunner.application.data.json"

    def delete_model(self, key, pipeline, index):
        models = self.settings.models.get()
        models[key][pipeline].pop(index)
        self.settings.models.set(models)
        self.save_settings()

    def available_models(self) -> dict:
        data = self.settings.models.get()
        models = {}

        for section in data.keys():
            for pipeline in data[section].keys():
                if pipeline not in models:
                    models[pipeline] = []
                models[pipeline].extend(data[section][pipeline])

        return models

    def available_categories(self):
        categories = []
        for section in self.settings.models.get().keys():
            for pipeline in self.settings.models.get()[section]:
                for item in self.settings.models.get()[section][pipeline]:
                    try:
                        category = item["category"]
                        if category not in categories:
                            categories.append(category)
                    except KeyError:
                        pass
        return categories

    def versions(self):
        versions = []
        for section in self.settings.models.get().keys():
            for pipeline in self.settings.models.get()[section].keys():
                for item in self.settings.models.get()[section][pipeline]:
                    if "version" in item:
                        version = item["version"]
                        if version not in versions and version != "" and version is not None:
                            versions.append(version)
        return versions

    def available_model_names(self, category, section, enabled_only=False):
        names = []
        for data in self.available_models_by_section(section):
            if isinstance(data, list):
                for item in data:
                    if item["category"] == category:
                        name = item["name"]
                        if name in names:
                            continue
                        if enabled_only and item["enabled"]:
                            names.append(name)
                        elif not enabled_only:
                            names.append(name)
            else:
                if data["category"] == category:
                    name = data["name"]
                    if name in names:
                        continue
                    if enabled_only and data["enabled"]:
                        names.append(name)
                    elif not enabled_only:
                        names.append(name)
        return names

    def available_models_by_section(self, section):
        models_by_section = []
        models = self.available_models()
        if section in models:
            models_by_section = models[section]
            if section == "img2img":
                models_by_section = [
                    *models_by_section,
                    *models["txt2img"]
                ]
        return models_by_section

    def available_pipeline_by_section(self, pipeline, version, category):
        pipelines = self.settings.pipelines.get()
        available_pipelines = {**pipelines["default"]}
        for key in pipelines["custom"].keys():
            available_pipelines[key] = pipelines["custom"][key]

        return available_pipelines.get(pipeline, {}).get(version, {}).get(category, {})

    def set_model_enabled(self, key, model, enabled):
        for pipeline_model in self.settings.models.get()[key][model["pipeline_action"]]:
            if pipeline_model["name"] == model["name"] and \
               pipeline_model["path"] == model["path"] and \
               pipeline_model["branch"] == model["branch"] and \
               pipeline_model["version"] == model["version"] and \
               pipeline_model["category"] == model["category"]:
                pipeline_model["enabled"] = enabled == 2
        self.save_settings()

    def reset_settings_to_default(self, default_settings):
        self.settings.version.set(default_settings["version"])
        self.settings.controlnet_models.set(default_settings["controlnet_models"])
        current_models = self.settings.models.get()
        models = default_settings["models"]
        current_models["default"] = models["default"]
        self.settings.models.set(current_models)
        self.settings.pipelines.set(default_settings["pipelines"])
        self.save_settings()


    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        cls.app = app
        return cls._instance

    def __init__(self):
        self.settings = ApplicationSettings(app=self)
        self.settings.initialize(self.settings.read())
        try:
            self.load_settings()
        except Exception as e:
            self.save_settings()

        # check load_default_settings against self.settings for version
        # and update default values with new default values if version doesn't
        # match.
        default_settings = self.load_default_settings()
        if self.settings.version.get() != default_settings["version"]:
            self.reset_settings_to_default(default_settings=default_settings)
            self.save_settings()
