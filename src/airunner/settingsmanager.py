import json
import os
import pickle

from aihandler.database import RunAISettings
from aihandler.qtvar import BooleanVar, StringVar, IntVar, FloatVar, DoubleVar

available_tools = [
    "",
    # "select",
    "pen",
    # "eraser",
    # "fill",
]




class SettingsManager:
    app = None
    settings = None

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


    def __init__(self, app=None):
        self.settings = RunAISettings(app=self)
        self.settings.initialize(self.settings.read())
        self.font_name = "song ti"
        self.font_size = 9
        try:
            self.load_settings()
        except Exception as e:
            self.save_settings()

    def save_settings(self):
        HOME = os.path.expanduser("~")
        with open(os.path.join(HOME, "airunner_settings.json"), "w") as f:
            settings = {}
            for key, value in self.settings.__dict__.items():
                if isinstance(value, BooleanVar):
                    settings[key] = value.get()
                elif isinstance(value, StringVar):
                    settings[key] = value.get()
                elif isinstance(value, IntVar):
                    settings[key] = value.get()
                elif isinstance(value, FloatVar):
                    settings[key] = value.get()
                elif isinstance(value, DoubleVar):
                    settings[key] = value.get()
            json.dump(settings, f)

    def load_settings(self):
        HOME = os.path.expanduser("~")
        path = os.path.join(HOME, "airunner_settings.json")
        # check if exists
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            settings = json.load(f)
            for key, value in self.settings.__dict__.items():
                if isinstance(value, BooleanVar):
                    value.set(settings[key])
                elif isinstance(value, StringVar):
                    value.set(settings[key])
                elif isinstance(value, IntVar):
                    value.set(settings[key])
                elif isinstance(value, FloatVar):
                    value.set(settings[key])
                elif isinstance(value, DoubleVar):
                    value.set(settings[key])



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

    def set_tool(self, val):
        self.settings.current_tool.set(val)