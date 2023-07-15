import os
import json
from aihandler.database import RunAISettings, PromptSettings
from aihandler.qtvar import Var, BooleanVar, StringVar, IntVar, FloatVar, DoubleVar, ListVar
# from aihandler.qtvar import ExtensionVar  TODO: extensions

available_tools = [
    "",
    # "select",
    "pen",
    # "eraser",
    # "fill",
]


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

    @property
    def padding(self):
        return 5

    @property
    def bold_font(self):
        return (
            self.font_name,
            self.font_size,
            "bold"
        )

    @property
    def font(self):
        return (
            self.font_name,
            self.font_size
        )

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
        self.font_name = "song ti"
        self.font_size = 9
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
                """
                TODO: extensions
                if key in ["available_extensions", "active_extensions"]:
                    continue
                elif key == "enabled_extensions":
                    enabled_ext = []
                    for ext in value.get():
                        enabled_ext.append(ext)
                    settings[key] = enabled_ext
                else:
                    settings[key] = value.get()
                """
                settings[key] = value.get()
            elif type(value) in [list, dict, int, float, str, bool]:
                settings[key] = value
        HOME = os.path.expanduser("~")
        f = open(os.path.join(HOME, self.file_name), "w")
        json.dump(settings, f)

    def load_settings(self):
        self.disable_save()
        HOME = os.path.expanduser("~")
        f = open(os.path.join(HOME, self.file_name), "r")
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

    def set_prompt_triggers(self):
        # cur_model = self.model_var.get()
        # if cur_model != "":
        #     cur_model = cur_model.split("/")[-1]
        # models = MODELS[self.model_version.get()]
        # for model in models:
        #     if model["name"] == cur_model:
        #         prompt_triggers = model["prompt_triggers"] if "prompt_triggers" in model else []
        #         self.prompt_triggers.set("Prompt Triggers: " + ", ".join(prompt_triggers))
        #         return
        # self.prompt_triggers.set("")
        pass

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

    def set_tool(self, val):
        self.settings.current_tool.set(val)


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
        self.font_name = "song ti"
        self.font_size = 9
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
                """
                TODO: extensions
                if key in ["available_extensions", "active_extensions"]:
                    continue
                elif key == "enabled_extensions":
                    enabled_ext = []
                    for ext in value.get():
                        enabled_ext.append(ext)
                    settings[key] = enabled_ext
                else:
                    settings[key] = value.get()
                """
                settings[key] = value.get()
            elif type(value) in [list, dict, int, float, str, bool]:
                settings[key] = value
        HOME = os.path.expanduser("~")
        f = open(os.path.join(HOME, self.file_name), "w")
        json.dump(settings, f)

    def load_settings(self):
        self.disable_save()
        HOME = os.path.expanduser("~")
        f = open(os.path.join(HOME, self.file_name), "r")
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
