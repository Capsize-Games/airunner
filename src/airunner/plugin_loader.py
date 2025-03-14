import importlib.util
import os
import sys


class PluginLoader:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir

    def load_plugins(self):
        plugins = []
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py"):
                plugin_path = os.path.join(self.plugin_dir, filename)
                module_name = os.path.splitext(filename)[0]
                spec = importlib.util.spec_from_file_location(module_name, plugin_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Check if the module has a `Plugin` class
                if hasattr(module, "Plugin"):
                    plugins.append(module.Plugin())

        return plugins
