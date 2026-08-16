"""QSettings-backed accessors for client-local settings.

Issue 101/301 split the settings stores: service-owned fields stay in the
daemon database (``resource_store`` / ``ApplicationSettings`` etc.), while
client-local preferences — theme, window state, wizard/agreement completion
flags, canvas tool selection, GUI language — live in QSettings
(``AIRUNNER_BASE_PATH/config/settings.ini`` via :func:`get_qsettings`).

The alembic migration ``move_client_local_application_settings_to_qsettings``
already moved the data at the database layer; this module is the GUI-side
read/write seam so components stop hitting deprecated DB columns.

The field list mirrors that migration's ``_CLIENT_LOCAL_APPLICATION_SETTINGS``
map so the two stay in lockstep.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtCore import QSettings

from airunner.utils.settings.get_qsettings import get_qsettings


#: Client-local application settings migrated out of the shared database.
#: Keyed by the canonical field name; values are (QSettings group, default).
CLIENT_LOCAL_SETTINGS: dict[str, tuple[str, Any]] = {
    "active_grid_size_lock": ("application_settings", False),
    "age_agreement_checked": ("application_settings", False),
    "airunner_agreement_checked": ("application_settings", False),
    "current_layer_index": ("application_settings", 0),
    "current_tool": ("application_settings", "brush"),
    "dark_mode_enabled": ("application_settings", True),
    "download_wizard_completed": ("application_settings", False),
    "generator_section": ("application_settings", ""),
    "image_to_new_layer": ("application_settings", False),
    "is_maximized": ("window_settings", False),
    "latest_version_check": ("application_settings", False),
    "llama_license_agreement_checked": ("application_settings", False),
    "override_system_theme": ("application_settings", False),
    "paths_initialized": ("application_settings", False),
    "pivot_point_x": ("application_settings", 0),
    "pivot_point_y": ("application_settings", 0),
    "resize_on_paste": ("application_settings", False),
    "run_setup_wizard": ("application_settings", True),
    "show_active_image_area": ("application_settings", True),
    "stable_diffusion_agreement_checked": ("application_settings", False),
    "user_agreement_checked": ("application_settings", False),
}

#: Fields the GUI still reads through the settings layer that map 1:1 onto
#: ``CLIENT_LOCAL_SETTINGS`` keys (documented convenience surface).
_READERS: dict[str, Callable[[], Any]] = {}


def _settings() -> QSettings:
    """Return the shared QSettings instance (INI under AIRUNNER_BASE_PATH)."""
    return get_qsettings()


def get_client_setting(
    name: str,
    default: Any = None,
    type_: Optional[type] = None,
) -> Any:
    """Read one client-local setting from QSettings.

    ``default`` falls back to the field's documented default from
    :data:`CLIENT_LOCAL_SETTINGS` when not supplied.
    """
    if name not in CLIENT_LOCAL_SETTINGS:
        return default
    group, fallback = CLIENT_LOCAL_SETTINGS[name]
    settings = _settings()
    settings.beginGroup(group)
    try:
        value = settings.value(name, fallback if default is None else default, type=type_)
    finally:
        settings.endGroup()
    return value


def set_client_setting(name: str, value: Any) -> None:
    """Write one client-local setting to QSettings and sync it to disk.

    ``None`` values are not persisted — they are treated as "unset", so the
    documented default (see :data:`CLIENT_LOCAL_SETTINGS`) applies on read.
    """
    if name not in CLIENT_LOCAL_SETTINGS or value is None:
        return
    group, _ = CLIENT_LOCAL_SETTINGS[name]
    settings = _settings()
    settings.beginGroup(group)
    try:
        settings.setValue(name, value)
    finally:
        settings.endGroup()
    settings.sync()


def is_dark() -> bool:
    """Return whether the dark theme is enabled (client-local)."""
    return bool(get_client_setting("dark_mode_enabled", type_=bool))


def set_dark(enabled: bool) -> None:
    """Set the dark-theme preference (client-local)."""
    set_client_setting("dark_mode_enabled", bool(enabled))


def current_tool() -> Optional[str]:
    """Return the active canvas tool name (client-local).

    Returns ``None`` when no tool has been persisted yet (callers fall back
    to their own default, matching the pre-split behavior of a NULL column).
    """
    value = get_client_setting("current_tool", type_=str)
    if value is None or value == "":
        return None
    return str(value)


def set_current_tool(tool: str) -> None:
    """Set the active canvas tool (client-local)."""
    set_client_setting("current_tool", tool)


def run_setup_wizard() -> bool:
    """Return whether the setup wizard should run on next launch."""
    return bool(get_client_setting("run_setup_wizard", type_=bool))


def is_maximized() -> bool:
    """Return whether the main window was last maximized (client-local)."""
    return bool(get_client_setting("is_maximized", type_=bool))


def override_system_theme() -> bool:
    """Return whether the user overrides the system theme (client-local)."""
    return bool(get_client_setting("override_system_theme", type_=bool))


def generator_section() -> str:
    """Return the last-used image generator section (client-local)."""
    return str(get_client_setting("generator_section"))


__all__ = [
    "CLIENT_LOCAL_SETTINGS",
    "get_client_setting",
    "set_client_setting",
    "is_dark",
    "set_dark",
    "current_tool",
    "set_current_tool",
    "run_setup_wizard",
    "is_maximized",
    "override_system_theme",
    "generator_section",
]
