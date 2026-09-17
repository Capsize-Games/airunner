"""Service-owned QSettings factory (issue #2186).

``QSettings`` reads/writes are a boundary crossing that a few database
models and the daemon resource store need, but the factory itself has no
desktop-specific behaviour: it only needs ``AIRUNNER_BASE_PATH`` and
PySide6. It previously lived solely at
``airunner.utils.settings.get_qsettings``, which made ``airunner_services``
import ``airunner`` to reach it -- an install-breaking cycle, since
``airunner_services`` is a declared dependency of ``airunner``. This is a
service-owned copy so callers here never import the desktop package.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from airunner_common.settings import AIRUNNER_BASE_PATH

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings


def get_qsettings() -> QSettings:
    """Get a QSettings instance that persists to AIRUNNER_BASE_PATH.

    This ensures settings are saved within the persistent data directory,
    which is important for Docker environments where the home directory
    may not be mounted as a volume.

    PySide6 is imported lazily so merely importing this module -- or
    the ``airunner_services.utils.settings`` package that re-exports
    it -- never requires PySide6 to be installed. A module-level
    import here would make every caller's own try/except ImportError
    guard (see application_settings.py, resource_store.py) too late:
    the package __init__ importing this function would already have
    failed (issue #2193's PySide6-at-module-scope rule).
    """
    from PySide6.QtCore import QSettings

    config_path = os.path.join(AIRUNNER_BASE_PATH, "config", "settings.ini")

    config_dir = os.path.dirname(config_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    return QSettings(config_path, QSettings.Format.IniFormat)
