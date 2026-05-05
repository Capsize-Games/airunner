"""Persist the active AIRunner coding project for shared UI context."""

import os

from airunner.utils.settings import get_qsettings


_SETTINGS_GROUP = "coding_workspace"
_ACTIVE_PROJECT_KEY = "active_project_path"


def get_active_project_path() -> str | None:
    """Return the active coding project path, if one is set."""
    settings = get_qsettings()
    settings.beginGroup(_SETTINGS_GROUP)
    value = settings.value(_ACTIVE_PROJECT_KEY, "", type=str)
    settings.endGroup()
    if not value:
        return None
    return os.path.abspath(os.path.expanduser(value))


def set_active_project_path(project_path: str | None) -> None:
    """Persist the active coding project path for other widgets."""
    settings = get_qsettings()
    settings.beginGroup(_SETTINGS_GROUP)
    value = ""
    if project_path:
        value = os.path.abspath(os.path.expanduser(project_path))
    settings.setValue(_ACTIVE_PROJECT_KEY, value)
    settings.endGroup()