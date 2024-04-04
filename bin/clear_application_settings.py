from airunner.settings import ORGANIZATION, APPLICATION_NAME
from PySide6.QtCore import QSettings


def clear_application_settings():
    application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
    application_settings.clear()
    application_settings.sync()


clear_application_settings()
