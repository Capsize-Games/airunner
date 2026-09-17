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

import os

from PySide6.QtCore import QSettings

from airunner_common.settings import AIRUNNER_BASE_PATH


def get_qsettings() -> QSettings:
    """Get a QSettings instance that persists to AIRUNNER_BASE_PATH.

    This ensures settings are saved within the persistent data directory,
    which is important for Docker environments where the home directory
    may not be mounted as a volume.
    """
    config_path = os.path.join(AIRUNNER_BASE_PATH, "config", "settings.ini")

    config_dir = os.path.dirname(config_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    return QSettings(config_path, QSettings.Format.IniFormat)
