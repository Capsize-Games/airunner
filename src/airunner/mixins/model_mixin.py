import os
from aihandler.settings import MODELS
from airunner.mixins.base_mixin import BaseMixin


class ModelMixin(BaseMixin):
    def refresh_model_list(self):
        for i in range(self.window.tabWidget.count()):
            self.load_model_by_section(self.window.tabWidget.widget(i), self.sections[i])

    def load_model_by_section(self, tab, section_name):
        if section_name in ["txt2img", "img2img"]:
            section_name = "generate"
        models = self.load_default_models(section_name)
        models += self.load_models_from_path()
        self.models = models
        tab.model_dropdown.addItems(models)

    def load_default_models(self, section_name):
        return [
            k for k in MODELS[section_name].keys()
        ]

    def load_models_from_path(self):
        path = os.path.join(self.settings_manager.settings.model_base_path.get())
        if os.path.exists(path):
            return [os.path.join(path, model) for model in os.listdir(path)]
        return []