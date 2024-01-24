from PyQt6.QtCore import QObject

from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.aihandler.logger import Logger


class BaseHandler(QObject, MediatorMixin, SettingsMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        SettingsMixin.__init__(self)
        MediatorMixin.__init__(self)
        self.logger = Logger(prefix=self.__class__.__name__)
