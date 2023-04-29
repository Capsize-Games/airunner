import importlib
import os
from aihandler.util import get_extensions_from_path


class ExtensionMixin:
    """
    This is a mixin class that is used to manage extensions.
    """
    settings_manager = None
    active_extensions = []

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
        extension_path = os.path.join(base_path, "extensions")
        if not os.path.exists(extension_path):
            return extensions
        available_extensions = get_extensions_from_path(extension_path)
        for extension in available_extensions:
            if extension.name.get() in self.settings_manager.settings.enabled_extensions.get():
                repo = extension.repo.get()
                name = repo.split("/")[-1]
                path = os.path.join(extension_path, name)
                if os.path.exists(path):
                    print(path)
                    for f in os.listdir(path):
                        if os.path.isfile(os.path.join(path, f)) and f == "main.py":
                            # get Extension class from main.py
                            spec = importlib.util.spec_from_file_location("main", os.path.join(path, f))
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            extension_class = getattr(module, "Extension")
                            extensions.append(extension_class(self.settings_manager))
        self.settings_manager.settings.active_extensions.set(extensions)
