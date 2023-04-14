import os
from PyQt6 import uic


class BaseExtension:
    """
    An extension interface for the AI Runner GUI
    """
    extension_directory = None

    def __init__(self, settings_manager=None):
        self._settings_manager = settings_manager

    @property
    def settings(self):
        return self._settings_manager.settings

    @property
    def model_base_path(self):
        return self._settings_manager.settings.model_base_path.get()

    def load_template(self, template_name):
        path = self.model_base_path
        return uic.loadUi(os.path.join(path, "extensions", self.extension_directory, "templates", f"{template_name}.ui"))

    def generator_tab_injection(self, tab, name=None):
        """
        Override this method to inject a widget into one or more generator tabs
        eg txt2img, img2img, controlnet etc.
        :param name: string name of the tab
        :param tab: the tab widget
        :return:
        """
        pass
