import os
import json

from filelock import FileLock

from airunner.aihandler.database import RunAISettings, PromptSettings
from airunner.aihandler.qtvar import Var, BooleanVar, StringVar, IntVar, FloatVar, DoubleVar, ListVar


class SettingsManager:
    _instance = None
    app = None
    settings = None
    save_disabled = False

    @property
    def file_name(self):
        return "airunner.settings.json"

    @property
    def current_tool(self):
        return self.settings.current_tool.get()

    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(app=app)
        cls.app = app
        return cls._instance

    def __init__(self, app=None):
        # if not app:
        #     raise Exception("SettingsManager must be initialized with an app")
        self.settings = RunAISettings(app=self)
        self.settings.initialize(self.settings.read())
        try:
            self.load_settings()
        except Exception as e:
            self.save_settings()

    def disable_save(self):
        self.save_disabled = True

    def enable_save(self):
        self.save_disabled = False

    def save_settings(self):
        if self.save_disabled:
            return
        settings = {}
        for key, value in self.settings.__dict__.items():
            if isinstance(value, Var):
                settings[key] = value.get()
            elif type(value) in [list, dict, int, float, str, bool]:
                settings[key] = value
        HOME = os.path.expanduser("~")
        lock = FileLock(os.path.join(HOME, self.file_name + ".lock"))
        with lock:
            with open(os.path.join(HOME, self.file_name), "w") as f:
                json.dump(settings, f)

    def load_settings(self):
        self.disable_save()
        HOME = os.path.expanduser("~")
        lock = FileLock(os.path.join(HOME, self.file_name + ".lock"))
        with lock:
            with open(os.path.join(HOME, self.file_name), "r") as f:
                try:
                    settings = json.load(f)
                except Exception as e:
                    settings = {}
        for key in settings.keys():
            value = settings[key]
            try:
                self.settings.__dict__[key].set(value)
            except Exception as e:
                self.settings.__dict__[key] = value
        self.enable_save()

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


class PromptManager:
    _instance = None
    app = None
    settings = None
    save_disabled = False

    @property
    def file_name(self):
        return "airunner.prompts.json"

    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(app=app)
        cls.app = app
        return cls._instance

    def __init__(self, app=None):
        # if not app:
        #     raise Exception("SettingsManager must be initialized with an app")
        self.settings = PromptSettings(app=self)
        self.settings.initialize(self.settings.read())
        try:
            self.load_settings()
        except Exception as e:
            self.save_settings()

    def disable_save(self):
        self.save_disabled = True

    def enable_save(self):
        self.save_disabled = False

    def save_settings(self):
        if self.save_disabled:
            return
        settings = {}
        for key, value in self.settings.__dict__.items():
            if isinstance(value, Var):
                settings[key] = value.get()
            elif type(value) in [list, dict, int, float, str, bool]:
                settings[key] = value
        HOME = os.path.expanduser("~")
        lock = FileLock(os.path.join(HOME, self.file_name + ".lock"))
        with lock:
            with open(os.path.join(HOME, self.file_name), "w") as f:
                json.dump(settings, f)

    def load_settings(self):
        self.disable_save()
        HOME = os.path.expanduser("~")
        lock = FileLock(os.path.join(HOME, self.file_name + ".lock"))
        with lock:
            with open(os.path.join(HOME, self.file_name), "r") as f:
                try:
                    settings = json.load(f)
                except Exception as e:
                    settings = {}
        for key in settings.keys():
            value = settings[key]
            try:
                self.settings.__dict__[key].set(value)
            except Exception as e:
                self.settings.__dict__[key] = value
        self.enable_save()


class ApplicationData:
    _instance = None
    app = None
    settings = None
    save_disabled = False

    @property
    def file_name(self):
        return "application_data.json"

    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(app=app)
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

    def disable_save(self):
        self.save_disabled = True

    def enable_save(self):
        self.save_disabled = False

    def save_settings(self):
        if self.save_disabled:
            return
        settings = {}
        for key, value in self.settings.__dict__.items():
            if isinstance(value, Var):
                settings[key] = value.get()
            elif type(value) in [list, dict, int, float, str, bool]:
                settings[key] = value
        HOME = os.path.expanduser("~")
        lock = FileLock(os.path.join(HOME, self.file_name + ".lock"))
        with lock:
            with open(os.path.join(HOME, self.file_name), "w") as f:
                json.dump(settings, f)

    def load_settings(self):
        self.disable_save()
        HOME = os.path.expanduser("~")
        lock = FileLock(os.path.join(HOME, self.file_name + ".lock"))
        with lock:
            with open(os.path.join(HOME, self.file_name), "r") as f:
                try:
                    settings = json.load(f)
                except Exception as e:
                    settings = {}
        for key in settings.keys():
            value = settings[key]
            try:
                self.settings.__dict__[key].set(value)
            except Exception as e:
                self.settings.__dict__[key] = value
        self.enable_save()
