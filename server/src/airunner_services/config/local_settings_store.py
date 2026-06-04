"""Service-owned local settings helpers backed by AIRunner's INI file."""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Mapping

from airunner_services.settings import AIRUNNER_BASE_PATH


_TRUE_VALUES = {"1", "true", "yes", "on"}


def get_setting(key: str, default: str = "") -> str:
    """Return one string setting from the local settings file."""
    config = _read_config()
    section, option = _split_key(key)
    return config.get(section, option, fallback=default)


def get_bool_setting(key: str, default: bool = False) -> bool:
    """Return one boolean setting from the local settings file."""
    value = get_setting(key, _serialize_value(default))
    return str(value).strip().lower() in _TRUE_VALUES


def set_setting(key: str, value: str | bool) -> None:
    """Persist one setting to the local settings file."""
    set_settings({key: value})


def set_settings(values: Mapping[str, str | bool]) -> None:
    """Persist multiple settings to the local settings file."""
    config = _read_config()
    for key, value in values.items():
        section, option = _split_key(key)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, _serialize_value(value))
    _write_config(config)


def _settings_path() -> Path:
    """Return the shared on-disk settings file path."""
    return Path(AIRUNNER_BASE_PATH) / "config" / "settings.ini"


def _read_config() -> configparser.ConfigParser:
    """Return the current local settings file as a config parser."""
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    path = _settings_path()
    if path.is_file():
        config.read(path, encoding="utf-8")
    return config


def _write_config(config: configparser.ConfigParser) -> None:
    """Write one config parser back to the local settings file."""
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        config.write(handle)


def _split_key(key: str) -> tuple[str, str]:
    """Split one settings key into its INI section and option."""
    section, separator, option = key.partition("/")
    if not separator or not section or not option:
        raise ValueError(f"Invalid settings key: {key}")
    return section, option


def _serialize_value(value: str | bool) -> str:
    """Serialize one settings value for INI persistence."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


__all__ = [
    "get_bool_setting",
    "get_setting",
    "set_setting",
    "set_settings",
]