# This module contains the base API service class for all API services.
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from PySide6.QtCore import QObject


class APIServiceBase(MediatorMixin, SettingsMixin, QObject):
    """Base class for all API services.

    Provides signal-based communication via MediatorMixin and
    settings access via SettingsMixin.
    """

    def __init__(self):
        super().__init__()
