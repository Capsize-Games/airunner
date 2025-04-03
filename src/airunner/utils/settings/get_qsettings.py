from PySide6.QtCore import QSettings
from airunner.settings import AIRUNNER_ORGANIZATION, AIRUNNER_APPLICATION_NAME


def get_qsettings() -> QSettings:
    return QSettings(AIRUNNER_ORGANIZATION, AIRUNNER_APPLICATION_NAME)
