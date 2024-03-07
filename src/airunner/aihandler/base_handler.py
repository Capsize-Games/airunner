import torch

from PyQt6.QtCore import QObject

from airunner.enums import HandlerType
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.aihandler.logger import Logger
from airunner.utils import get_torch_device


class BaseHandler(
    QObject,
    MediatorMixin
):
    """
    Base class for all AI handlers.
    AI Handlers are classes which load and process AI models.
    They are typically instantiated by workers.
    """
    handler_type = HandlerType.TRANSFORMER

    def __init__(self, *args, **kwargs):
        self.use_gpu = True
        self.logger = Logger(prefix=self.__class__.__name__)
        MediatorMixin.__init__(self)
        super().__init__(*args, **kwargs)

    @property
    def device(self):
        return get_torch_device()

    @property
    def llm_dtype(self):
        return self.settings["llm_generator_settings"]["dtype"]

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
    def torch_dtype(self):
        return torch.float16 if self.use_cuda else torch.float32

    @property
    def settings(self):
        return ServiceLocator.get("get_settings")()

    @settings.setter
    def settings(self, value):
        ServiceLocator.get("set_settings")(value)
