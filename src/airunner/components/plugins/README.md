# Plugin Loader

This directory contains the plugin loader and instructions for writing plugins for Airunner.

## How the Plugin Loader Works

The `PluginLoader` class dynamically loads plugins from a specified directory. Each plugin must be placed in its own subdirectory inside the plugin directory, and must contain a `plugin.py` file that defines a `Plugin` class.

### Plugin Directory Structure

```
plugins/
    my_plugin/
        plugin.py
    another_plugin/
        plugin.py
```

### Writing a Plugin

1. **Create a subdirectory** under the plugins directory (e.g., `my_plugin`).
2. **Add a `plugin.py` file** inside your plugin directory.
3. **Define a `Plugin` class** in `plugin.py`. This class can have any methods or properties you need.

#### Example

```python
# plugins/my_plugin/plugin.py

class Plugin:
    def __init__(self):
        print("My Plugin Initialized!")

    def run(self):
        print("Plugin logic goes here.")
```

### How Plugins Are Loaded

- The loader scans each subdirectory in the plugin directory.
- If a `plugin.py` file exists, it is loaded as a module.
- If the module defines a `Plugin` class, an instance is created and added to the plugins list.

### Usage

```python
from plugin_loader import PluginLoader

loader = PluginLoader("plugins")
plugins = loader.load_plugins()

for plugin in plugins:
    plugin.run()
```

## Notes

- Each plugin must define a `Plugin` class in `plugin.py`.
- The loader restores `sys.path` after loading each plugin to avoid conflicts.