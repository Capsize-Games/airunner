import torch
from PySide6.QtCore import QObject
from airunner.enums import HandlerType, SignalCode, ModelType, ModelStatus
from airunner.mediator_mixin import MediatorMixin
from airunner.aihandler.logger import Logger
from airunner.utils.get_torch_device import get_torch_device
from airunner.windows.main.settings_mixin import SettingsMixin


class BaseHandler(
    QObject,
    MediatorMixin,
    SettingsMixin
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
        SettingsMixin.__init__(self)
        super().__init__(*args, **kwargs)
        self.model_type = None

    @property
    def device(self):
        if not self.model_type:
            raise ValueError("model_type not set")
        return get_torch_device(self.settings["memory_settings"]["default_gpu"][self.model_type])

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

    def change_model_status(self, model: ModelType, status: ModelStatus, path: str):
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": model,
                "status": status,
                "path": path
            }
        )
