import os
from PySide6.QtCore import QSettings
from airunner.settings import (
    AIRUNNER_ORGANIZATION,
    AIRUNNER_APPLICATION_NAME,
    AIRUNNER_BASE_PATH,
)


def get_qsettings() -> QSettings:
    """Get a QSettings instance that persists to the AIRUNNER_BASE_PATH.
    
    This ensures settings are saved within the persistent data directory,
    which is important for Docker environments where the home directory
    may not be mounted as a volume.
    """
    # Use INI format and store in the persistent base path
    config_path = os.path.join(AIRUNNER_BASE_PATH, "config", "settings.ini")
    
    # Ensure the config directory exists
    config_dir = os.path.dirname(config_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    
    return QSettings(config_path, QSettings.Format.IniFormat)
