"""Load explicitly enabled GUI plugins from the user plugin directory."""

import importlib.util
import sys
from pathlib import Path
from typing import Optional

from airunner.extension_manifest import (
    PLUGIN_ALLOWLIST_ENV,
    load_enabled_extension_ids,
    resolve_enabled_manifest,
)


class PluginLoader:
    """Manifest-gated loader for external GUI plugins."""

    def __init__(self, plugin_dir: str) -> None:
        self.plugin_dir = Path(plugin_dir)

    def load_plugins(self):
        """Load explicitly enabled plugins with valid manifests only."""
        plugins = []
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        enabled_ids = load_enabled_extension_ids(PLUGIN_ALLOWLIST_ENV)
        if not enabled_ids:
            return plugins

        children = sorted(self.plugin_dir.iterdir(), key=lambda path: path.name)
        for child in children:
            plugin = self._load_plugin(child, enabled_ids)
            if plugin is not None:
                plugins.append(plugin)

        return plugins

    def _load_plugin(
        self,
        plugin_dir: Path,
        enabled_ids: set[str],
    ) -> Optional[object]:
        """Load one allowlisted plugin instance."""
        if not plugin_dir.is_dir():
            return None
        manifest = resolve_enabled_manifest(
            plugin_dir,
            default_entry_point="plugin.py",
            enabled_ids=enabled_ids,
            expected_kind="plugin",
        )
        if manifest is None:
            return None
        return self._instantiate_plugin(manifest.module_name, manifest.entry_path)

    def _instantiate_plugin(
        self,
        module_name: str,
        plugin_path: Path,
    ) -> Optional[object]:
        """Import a plugin module and instantiate its Plugin class."""
        original_sys_path = sys.path.copy()
        sys.path.append(str(plugin_path.parent))
        try:
            spec = importlib.util.spec_from_file_location(
                f"plugin_{module_name}",
                plugin_path,
            )
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin_class = getattr(module, "Plugin", None)
            return plugin_class() if plugin_class is not None else None
        finally:
            sys.path = original_sys_path
