import traceback
from PyQt6.QtCore import QObject
from aihandler.logger import logger
from aihandler.settings_manager import SettingsManager
from aihandler.settings import AIRUNNER_ENVIRONMENT, LOG_LEVEL, MessageCode


class BaseRunner(QObject):
    @property
    def is_dev_env(self):
        return AIRUNNER_ENVIRONMENT == "dev"

    def __init__(self, *args, **kwargs):
        super().__init__()
        logger.set_level(LOG_LEVEL)
        self.app = kwargs.get("app", None)
        self.settings_manager = kwargs.get("settings_manager", SettingsManager())
        self._message_var = kwargs.get("message_var", None)
        self._message_handler = kwargs.get("message_handler", None)

    def send_message(self, message, code=None):
        code = code or MessageCode.STATUS
        formatted_message = {
            "code": code,
            "message": message
        }
        if self._message_handler:
            self._message_handler(formatted_message)
        elif self._message_var:
            self._message_var.emit(formatted_message)

    def error_handler(self, error):
        message = str(error)
        if "got an unexpected keyword argument 'image'" in message and self.action in ["outpaint", "pix2pix", "depth2img"]:
            message = f"This model does not support {self.action}"
        traceback.print_exc()
        logger.error(error)
        self.send_message(message, MessageCode.ERROR)
