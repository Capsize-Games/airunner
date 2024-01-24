import torch

from PyQt6.QtCore import QObject

from airunner.aihandler.enums import HandlerType
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.aihandler.logger import Logger


class BaseHandler(QObject, MediatorMixin, SettingsMixin):
    """
    Base class for all AI handlers.
    AI Handlers are classes which load and process AI models.
    They are typically instantiated by workers.
    """
    handler_type = HandlerType.TRANSFORMER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        SettingsMixin.__init__(self)
        MediatorMixin.__init__(self)
        self.use_gpu = True
        self.logger = Logger(prefix=self.__class__.__name__)

    @property
    def llm_dtype(self):
        return self.llm_generator_settings["dtype"]

    @property
    def use_cuda(self):
        if self.handler_type == HandlerType.TRANSFORMER and (
            self.llm_dtype == "32bit" or not self.use_gpu
        ):
            return False
        return self.settings["use_cuda"] and torch.cuda.is_available()

    @property
    def cuda_index(self):
        return 0

    @property
    def device(self):
        return f"cuda:{self.cuda_index}" if self.use_cuda else "cpu"

    @property
    def torch_dtype(self):
        return torch.float16 if self.use_cuda else torch.float32
