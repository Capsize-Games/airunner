import torch
from PySide6.QtCore import QObject
from airunner.enums import HandlerType, SignalCode, ModelType, ModelStatus, ModelAction
from airunner.mediator_mixin import MediatorMixin
from airunner.handlers.logger import Logger
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
    model_type = None

    def __init__(self, *args, **kwargs):
        self._model_status = {model_type: ModelStatus.UNLOADED for model_type in ModelType}
        self.use_gpu = True
        self.logger = Logger(prefix=self.__class__.__name__)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__(*args, **kwargs)
        self._requested_action:ModelAction = ModelAction.NONE

    @property
    def model_status(self):
        return self._model_status[self.model_type]

    @property
    def requested_action(self):
        return self._requested_action

    @requested_action.setter
    def requested_action(self, value):
        self._requested_action = value

    def handle_requested_action(self):
        if self._requested_action is ModelAction.LOAD:
            self.load()
            self._requested_action = ModelAction.NONE
        if self._requested_action is ModelAction.CLEAR:
            self.unload()
            self._requested_action = ModelAction.NONE

    def load(self):
        raise NotImplementedError

    def unload(self):
        pass

    @property
    def device(self):
        if not self.model_type:
            raise ValueError("model_type not set")
        model_type_str = ""
        if self.model_type is ModelType.LLM:
            model_type_str = "llm"
        elif self.model_type is ModelType.TTS:
            model_type_str = "tts"
        elif self.model_type is ModelType.STT:
            model_type_str = "stt"
        elif self.model_type is ModelType.SD:
            model_type_str = "sd"
        return get_torch_device(
            getattr(
                self.memory_settings,
                f"default_gpu_{model_type_str}"
            )
        )

    @property
    def llm_dtype(self):
        return self.llm_generator_settings.dtype

    @property
    def use_cuda(self):
        if self.handler_type == HandlerType.TRANSFORMER and (
            self.llm_dtype == "32bit" or not self.use_gpu
        ):
            return False
        return self.application_settings.use_cuda and torch.cuda.is_available()

    @property
    def cuda_index(self):
        return 0

    @property
    def torch_dtype(self):
        return torch.float16 if self.use_cuda else torch.float32

    def change_model_status(self, model: ModelType, status: ModelStatus):
        self._model_status[model] = status
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": model,
                "status": status
            }
        )
