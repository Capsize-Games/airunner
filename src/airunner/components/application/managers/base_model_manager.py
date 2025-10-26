import torch
from abc import ABCMeta
from typing import Dict, Optional

from airunner.utils.memory import is_ampere_or_newer
from PySide6.QtCore import QObject

"""
The following code ensures that we only use PySide6 if it is available.
If it is not available, we use a placeholder class instead.
"""


class OptionalQObject(QObject):
    """Guard against PySide6 double-initialization errors in MRO."""

    def __init__(self, *args, **kwargs):
        if not hasattr(self, "_qobject_initialized"):
            super().__init__(*args, **kwargs)
            self._qobject_initialized = True


from airunner.enums import (
    HandlerType,
    ModelType,
    ModelStatus,
    ModelAction,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application import get_torch_device
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.application.managers.model_device_manager import (
    DeviceManagerMixin,
)
from airunner.components.application.managers.model_status_manager import (
    StatusManagerMixin,
)

try:
    from flash_attn import flash_attn_func
except ImportError:
    flass_attn_varlen_func = None
    flash_attn_func = None

QObjectMeta = type(OptionalQObject)


class CombinedMeta(QObjectMeta, ABCMeta):
    pass


from abc import ABC, abstractmethod


class ModelManagerInterface(ABC):
    @abstractmethod
    def load_model(self, *args, **kwargs):
        pass

    @abstractmethod
    def unload_model(self, *args, **kwargs):
        pass

    @abstractmethod
    def _load_model(self, *args, **kwargs):
        pass

    @abstractmethod
    def _unload_model(self, *args, **kwargs):
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
        if flash_attn_func:
            if "flash" in self.enabled_backends and is_ampere_or_newer(
                self.device_index
            ):
                return "flash_attention_2"
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
