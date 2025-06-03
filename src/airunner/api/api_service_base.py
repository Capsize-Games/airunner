# This module contains the base API service class for all API services.
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from PySide6.QtCore import QObject


class APIServiceBase(MediatorMixin, SettingsMixin, QObject):
    def __init__(self, emit_signal):
        super().__init__()
        self.emit_signal = emit_signal
