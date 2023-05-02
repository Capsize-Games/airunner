import os
from aihandler.settings import MODELS


class ModelMixin:
    def initialize(self):
        self.settings_manager.settings.model_base_path.my_signal.connect(self.refresh_model_list)

    def refresh_model_list(self):
        for i in range(self.window.tabWidget.count()):
            tab = self.window.tabWidget.widget(i)
            self.clear_model_list(tab)
            self.load_model_by_section(tab, self.sections[i])

    def clear_model_list(self, tab):
        tab.model_dropdown.clear()

    def load_model_by_section(self, tab, section_name):
        if section_name in ["txt2img", "img2img"]:
            section_name = "generate"
        models = self.load_default_models(section_name)
        models += self.load_models_from_path(self.settings_manager.settings.model_base_path.get())
        self.models = models
        tab.model_dropdown.addItems(models)

    def load_default_models(self, section_name):
        return [
            k for k in MODELS[section_name].keys()
        ]

    def load_models_from_path(self, path, models = None):
        if models is None:
            models = []
        if os.path.exists(path):
            for f in os.listdir(path):
                if os.path.isdir(os.path.join(path, f)):
                    models = self.load_models_from_path(os.path.join(path, f), models)
                elif f.endswith(".pt") or f.endswith(".safetensors") or f.endswith(".ckpt"):
                    models.append(f)
        return models