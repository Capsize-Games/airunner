import torch
from abc import ABC, abstractmethod, ABCMeta
from typing import Dict, Optional, List

from airunner.utils.memory import is_ampere_or_newer

"""
The following code ensures that we only use PySide6 if it is available.
If it is not available, we use a placeholder class instead.
"""
try:
    from PySide6.QtCore import QObject

    class OptionalQObject(QObject):
        pass

except ImportError:

    class OptionalQObject:
        """
        A placeholder class to avoid hard dependency on PySide6.
        """

        pass


from airunner.enums import (
    HandlerType,
    SignalCode,
    ModelType,
    ModelStatus,
    ModelAction,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application import get_torch_device
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.settings import (
    AIRUNNER_MEM_LLM_DEVICE,
    AIRUNNER_MEM_SD_DEVICE,
    AIRUNNER_MEM_TTS_DEVICE,
    AIRUNNER_MEM_STT_DEVICE,
)
from airunner.handlers.model_device_manager import DeviceManagerMixin
from airunner.handlers.model_status_manager import StatusManagerMixin

QObjectMeta = type(OptionalQObject)


class CombinedMeta(QObjectMeta, ABCMeta):
    pass


class BaseModelManager(
    MediatorMixin,
    SettingsMixin,
    OptionalQObject,
    DeviceManagerMixin,
    StatusManagerMixin,
    ABC,
    metaclass=CombinedMeta,
):
    """
    Base abstract class for all model handlers.
    Provides common functionality and interface for all handlers.
    """

    handler_type = HandlerType.TRANSFORMER
    model_type = None
    _model_status: Optional[Dict[ModelType, ModelStatus]] = None

    def __init__(self, *args, **kwargs):
        self.use_gpu = True
        super().__init__()
        self._requested_action: ModelAction = ModelAction.NONE
        self.logger.debug(
            f"Initialized instance {id(self)} with status: {self._model_status}"
        )

    @property
    def model_status(self) -> Dict:
        return self._model_status

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

    @abstractmethod
    def load(self):
        """
        Load the model and related components.
        """

    @abstractmethod
    def unload(self):
        """
        Unload the model and free resources.
        """

    @property
    def device(self):
        return get_torch_device(self.device_index)

    @property
    def attn_implementation(self) -> str:
        try:
            # raise NotImplementedError
            from flash_attn import flash_attn_varlen_func, flash_attn_func

            if "flash" in self.enabled_backends and is_ampere_or_newer(
                self.device_index
            ):
                return "flash_attention_2"
        except:
            pass
        return "sdpa"

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
