import importlib
import os
from aihandler.util import get_extensions_from_path


class ExtensionMixin:
    """
    This is a mixin class that is used to manage extensions.
    """
    active_extensions = []

    def initialize(self):
        for tab_name in self.tabs.keys():
            self.do_generator_tab_injection(self.tabs[tab_name], tab_name)
        self.do_menubar_injection()
        self.do_toolbar_injection()

    def get_extensions_from_path(self):
        """
        Initialize extensions by loading them from the extensions_directory.
        These are extensions that have been activated by the user.
        Extensions can be activated by manually adding them to the extensions folder
        or by browsing for them in the extensions menu and activating them there.

        This method initializes active extensions.
        :return:
        """
        extensions = []
        base_path = self.settings_manager.settings.model_base_path.get()
        extensions_path = self.settings_manager.settings.extensions_path.get() or "extensions"
        if extensions_path == "extensions":
            extensions_path = os.path.join(base_path, extensions_path)
        if not os.path.exists(extensions_path):
            return extensions
        available_extensions = get_extensions_from_path(extensions_path)
        for extension in available_extensions:
            if extension.name.get() in self.settings_manager.settings.enabled_extensions.get():
                repo = extension.repo.get()
                name = repo.split("/")[-1]
                path = os.path.join(extensions_path, name)
                if os.path.exists(path):
                    for f in os.listdir(path):
                        if os.path.isfile(os.path.join(path, f)) and f == "main.py":
                            # get Extension class from main.py
                            spec = importlib.util.spec_from_file_location("main", os.path.join(path, f))
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            ExtensionClass = getattr(module, "Extension")
                            try:
                                extensions.append(ExtensionClass(self, self.settings_manager))
                            except TypeError:
                                pass
        self.settings_manager.settings.active_extensions.set(extensions)

    def do_generator_tab_injection(self, tab, tab_name):
        """
        Ibjects extensions into the generator tab widget.
        :param tab_name:
        :param tab:
        :return:
        """
        for extension in self.settings_manager.settings.active_extensions.get():
            try:
                extension.generator_tab_injection(tab, tab_name)
            except AttributeError:
                pass

    def do_menubar_injection(self):
        for extension in self.settings_manager.settings.active_extensions.get():
            try:
                extension.menubar_injection(self.menubar)
            except AttributeError:
                pass

    def do_toolbar_injection(self):
        for extension in self.settings_manager.settings.active_extensions.get():
            try:
                extension.toolbar_injection(self.horizontalFrame)
            except AttributeError:
                pass

    def do_preferences_injection(self, window):
        for extension in self.settings_manager.settings.active_extensions.get():
            try:
                extension.preferences_injection(window)
            except AttributeError:
                pass

