import importlib.util
import os
import sys


class PluginLoader:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir

    def load_plugins(self):
        plugins = []
        if not os.path.exists(self.plugin_dir):
            try:
                os.makedirs(self.plugin_dir, exist_ok=True)
            except FileExistsError:
                pass

        for foldername in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(
                self.plugin_dir, foldername, "plugin.py"
            )
            path = os.path.join(self.plugin_dir, foldername)

            # Append the plugin directory to sys.path temporarily
            if os.path.isfile(plugin_path):
                original_sys_path = sys.path.copy()
                sys.path.append(path)

                try:
                    module_name = (
                        f"plugin_{foldername}"  # Use a unique module name
                    )
                    spec = importlib.util.spec_from_file_location(
                        module_name, plugin_path
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Check if the module has a `Plugin` class
                    if hasattr(module, "Plugin"):
                        plugins.append(module.Plugin())
                finally:
                    # Restore the original sys.path to avoid conflicts
                    sys.path = original_sys_path

        return plugins
