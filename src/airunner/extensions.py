import os
from PyQt6 import uic
from PyQt6.uic.exceptions import UIFileException


class BaseExtension:
    """
    An extension interface for the AI Runner GUI
    """
    extension_directory = None

    def __init__(self, app, settings_manager=None):
        self.app = app
        self.settings_manager = settings_manager

    @property
    def model_base_path(self):
        return self.settings_manager.settings.model_base_path.get()

    def save_settings(self):
        self.settings_manager.save_settings()

    def load_template(self, template_name):
        path = self.model_base_path
        extensions_path = self.settings_manager.settings.extensions_path.get() or "extensions"
        if extensions_path == "extensions":
            extensions_path = os.path.join(path, extensions_path)
        try:
            return uic.loadUi(os.path.join(extensions_path, self.extension_directory, "templates", f"{template_name}.ui"))
        except UIFileException:
            return None

    def generator_tab_injection(self, tab, name=None):
        """
        Override this method to inject a widget into one or more generator tabs
        eg txt2img, img2img, controlnet etc.
        :param name: string name of the tab
        :param tab: the tab widget
        :return:
        """
        pass

    def preferences_injection(self, window):
        """
        Override this method to inject a widget into the preferences window.
        :param preferences:
        :return:
        """
        pass
