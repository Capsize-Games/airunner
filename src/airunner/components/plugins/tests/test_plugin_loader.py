"""Tests for manifest-gated GUI plugin loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from airunner.components.plugins.plugin_loader import PluginLoader
from airunner.plugin_loader import PluginLoader as LegacyPluginLoader


def _write_plugin(
    root: Path,
    *,
    with_manifest: bool,
) -> Path:
    """Create a plugin package with a visible import side effect."""
    plugin_dir = root / "demo_plugin"
    plugin_dir.mkdir(parents=True)
    sentinel = plugin_dir / "imported.txt"
    sentinel_literal = repr(str(sentinel))
    if with_manifest:
        manifest = {
            "id": "demo.plugin",
            "name": "Demo Plugin",
            "version": "1.0.0",
            "kind": "plugin",
        }
        (plugin_dir / "airunner-extension.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
    (plugin_dir / "plugin.py").write_text(
        "from pathlib import Path\n"
        f"Path({sentinel_literal}).write_text('loaded', encoding='utf-8')\n"
        "class Plugin:\n"
        "    name = 'Demo Plugin'\n"
        "    def get_widget(self):\n"
        "        return None\n",
        encoding="utf-8",
    )
    return sentinel


@pytest.mark.parametrize(
    "loader_class",
    [PluginLoader, LegacyPluginLoader],
)
def test_plugin_loader_skips_plugins_without_allowlist(
    tmp_path,
    monkeypatch,
    loader_class,
):
    sentinel = _write_plugin(tmp_path, with_manifest=True)
    monkeypatch.delenv("AIRUNNER_ENABLED_PLUGINS", raising=False)

    plugins = loader_class(str(tmp_path)).load_plugins()

    assert plugins == []
    assert not sentinel.exists()


@pytest.mark.parametrize(
    "loader_class",
    [PluginLoader, LegacyPluginLoader],
)
def test_plugin_loader_requires_manifest(
    tmp_path,
    monkeypatch,
    loader_class,
):
    sentinel = _write_plugin(tmp_path, with_manifest=False)
    monkeypatch.setenv("AIRUNNER_ENABLED_PLUGINS", "demo.plugin")

    plugins = loader_class(str(tmp_path)).load_plugins()

    assert plugins == []
    assert not sentinel.exists()


@pytest.mark.parametrize(
    "loader_class",
    [PluginLoader, LegacyPluginLoader],
)
def test_plugin_loader_loads_allowlisted_manifest_plugin(
    tmp_path,
    monkeypatch,
    loader_class,
):
    sentinel = _write_plugin(tmp_path, with_manifest=True)
    monkeypatch.setenv("AIRUNNER_ENABLED_PLUGINS", "demo.plugin")

    plugins = loader_class(str(tmp_path)).load_plugins()

    assert len(plugins) == 1
    assert plugins[0].name == "Demo Plugin"
    assert sentinel.exists()