import torch
from abc import ABC, abstractmethod, ABCMeta
from typing import Dict, Optional

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

QObjectMeta = type(OptionalQObject)


class CombinedMeta(QObjectMeta, ABCMeta):
    pass


class BaseModelManager(
    MediatorMixin, SettingsMixin, OptionalQObject, ABC, metaclass=CombinedMeta
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
        # Initialize _model_status as an instance attribute
        super().__init__()
        self._requested_action: ModelAction = ModelAction.NONE
        # Initialize instance status using the specific class's model_status definition
        # Use getattr to safely get the class attribute from the actual instance's class
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
    def device_index(self):
        device = None
        model_type_str = ""
        if self.model_type is ModelType.LLM:
            device = AIRUNNER_MEM_LLM_DEVICE
            model_type_str = "llm"
        elif self.model_type is ModelType.TTS:
            device = AIRUNNER_MEM_TTS_DEVICE
            model_type_str = "tts"
        elif self.model_type is ModelType.STT:
            device = AIRUNNER_MEM_STT_DEVICE
            model_type_str = "stt"
        elif self.model_type is ModelType.SD:
            device = AIRUNNER_MEM_SD_DEVICE
            model_type_str = "sd"
        if device is None:
            if not self.model_type:
                raise ValueError("model_type not set")
            device = getattr(
                self.memory_settings, f"default_gpu_{model_type_str}"
            )
        return device

    @property
    def device(self):
        return get_torch_device(self.device_index)

    @property
    def attn_implementation(self) -> str:
        return (
            "flash_attention_2"
            if is_ampere_or_newer(self.device_index)
            else "sdpa"
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
        self.logger.debug(
            f"Instance {id(self)}: Attempting to change status for {model.name} to {status.name}"
        )  # Added instance ID
        if model in self._model_status:
            old_status = self._model_status.get(
                model, ModelStatus.UNLOADED
            )  # Get old status safely
            self._model_status[model] = status
            # Use f-string for clarity
            self.logger.info(
                f"Instance {id(self)}: Model {model.name} status changed from {old_status.name} to {status.name}"
            )
            self.api.change_model_status(model, status)
            self.logger.debug(
                f"Instance {id(self)}: Current status dict: {self._model_status}"
            )  # Added instance ID
        else:
            self.logger.warning(
                f"Instance {id(self)}: Attempted to change status for model type {model.name} not defined in this handler's initial status."
            )
