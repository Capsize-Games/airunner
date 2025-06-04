"""
Launcher for AI Runner that ensures UI files are built before starting the main application.

This script is used as the entry point for the `airunner` command.
"""

import sys
import logging
import importlib.util
import os

from airunner.data.models.airunner_settings import AIRunnerSettings

COMPONENTS_PATH = os.path.join(os.path.dirname(__file__), "components")


def deep_merge(defaults, current):
    """Recursively merge defaults into current, overwriting type mismatches and adding missing fields."""
    if not isinstance(defaults, dict) or not isinstance(current, dict):
        return defaults
    merged = dict(current)
    for k, v in defaults.items():
        if k not in merged:
            merged[k] = v
        else:
            if isinstance(v, dict) and isinstance(merged[k], dict):
                merged[k] = deep_merge(v, merged[k])
            elif type(merged[k]) != type(v):
                merged[k] = v
    # Optionally remove keys not in defaults (strict sync)
    # for k in list(merged.keys()):
    #     if k not in defaults:
    #         del merged[k]
    return merged


def register_component_settings():
    """Register settings for each component with a data/settings.py Pydantic dataclass."""
    import traceback

    created_count = 0
    found_count = 0

    for entry in os.scandir(COMPONENTS_PATH):
        if not entry.is_dir():
            continue
        settings_path = os.path.join(entry.path, "data", "settings.py")
        if not os.path.isfile(settings_path):
            continue
        spec = importlib.util.spec_from_file_location(
            f"airunner.components.{entry.name}.data.settings", settings_path
        )
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"[DEBUG] Processing module: {module.__name__}")
        for attr in dir(module):
            print(f"[DEBUG] Found attribute: {attr}")
            obj = getattr(module, attr)
            if (
                isinstance(obj, type)
                and hasattr(obj, "__fields__")
                and "name" in obj.__fields__
            ):
                print(f"[DEBUG] Processing settings class: {obj.__name__}")
                try:
                    instance = obj()
                    name = getattr(instance, "name", None)
                    print(f"[DEBUG] Settings instance name: {name}")
                    if not name:
                        continue
                    found_count += 1
                    existing = AIRunnerSettings.objects.filter_by(name=name)
                    if not existing:
                        data = (
                            instance.dict()
                            if hasattr(instance, "dict")
                            else instance.model_dump()
                        )
                        AIRunnerSettings.objects.create(name=name, data=data)
                        created_count += 1
                    else:
                        # Deep merge: update all fields to match dataclass, preserve user data where possible
                        defaults = (
                            instance.dict()
                            if hasattr(instance, "dict")
                            else instance.model_dump()
                        )
                        current = (
                            existing[0].data
                            if isinstance(existing, list) and existing
                            else existing.data
                        )
                        print(
                            f"\n[DEBUG] Existing data for {name}:\n{current}"
                        )
                        print(
                            f"[DEBUG] Expected (defaults) data for {name}:\n{defaults}\n"
                        )
                        merged = deep_merge(defaults, current)
                        for key in ("name", "id"):
                            if key in current:
                                merged[key] = current[key]
                        if merged != current:
                            print(
                                f"[DEBUG] Updating DB for {name} with merged data:\n{merged}\n"
                            )
                            AIRunnerSettings.objects.update_by(
                                {"name": name}, data=merged
                            )
                except Exception as e:
                    logging.warning(
                        f"Failed to create/update default settings for {attr}: {e}\n{traceback.format_exc()}"
                    )
    logging.info(
        f"register_component_settings: found {found_count} settings classes, created {created_count} new entries."
    )


def main():
    # Build UI files first
    try:
        from airunner.bin import build_ui

        build_ui.main()
    except Exception as e:
        logging.warning(f"UI build step failed: {e}")

    # Register component settings after UI build but before main app starts
    try:
        register_component_settings()
    except Exception as e:
        logging.error(f"Failed to register component settings: {e}")
        import traceback

        traceback.print_exc()

    # Only run the main app, no watcher logic
    from airunner.main import main as real_main

    sys.exit(real_main())
