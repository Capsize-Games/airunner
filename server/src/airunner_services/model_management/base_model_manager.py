"""Service-owned base class for shared model managers."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Optional

import torch

from airunner_services.utils.application.api_reference import (
    peek_registered_api,
)

from airunner_services.settings import AIRUNNER_MEM_LLM_DEVICE
from airunner_services.settings import AIRUNNER_MEM_SD_DEVICE
from airunner_services.settings import AIRUNNER_MEM_STT_DEVICE
from airunner_services.settings import AIRUNNER_MEM_TTS_DEVICE
from airunner_services.utils.application import get_torch_device
from airunner_services.utils.application import MediatorMixin
from airunner_services.utils.application import RuntimeContextMixin
from airunner_services.utils.application.runtime_primitives import QObject
from airunner_services.utils.memory.is_ampere_or_newer import (
    is_ampere_or_newer,
)

try:
    from flash_attn import flash_attn_func
except ImportError:
    flash_attn_func = None


class BaseModelManager(
    RuntimeContextMixin,
    MediatorMixin,
    QObject,
    ABC,
):
    """Provide shared service-safe model-manager behavior."""

    handler_type = "transformer"
    model_type = None
    _model_status: Optional[Dict[Any, Any]] = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.use_gpu = True
        super().__init__(*args, **kwargs)
        self._requested_action: Any = None
        self.logger.debug(
            "Initialized instance %s with status: %s",
            id(self),
            self._model_status,
        )

    @property
    def model_status(self) -> Dict[Any, Any]:
        """Return tracked model status values."""
        return self._model_status

    @property
    def requested_action(self) -> Any:
        """Return the current deferred action request."""
        return self._requested_action

    @requested_action.setter
    def requested_action(self, value: Any) -> None:
        """Store one deferred action request."""
        self._requested_action = value

    def handle_requested_action(self) -> None:
        """Execute one deferred load or unload request when present."""
        if self._requested_action_matches("LOAD"):
            self.load()
            self._clear_requested_action()
        if self._requested_action_matches("CLEAR"):
            self.unload()
            self._clear_requested_action()

    def _requested_action_matches(self, expected_name: str) -> bool:
        """Return whether the current action matches one expected name."""
        action = self._requested_action
        if action is None:
            return False
        if getattr(action, "name", None) == expected_name:
            return True
        return str(action).split(".")[-1] == expected_name

    def _clear_requested_action(self) -> None:
        """Reset the deferred request back to the enum NONE value."""
        action = self._requested_action
        action_type = getattr(action, "__class__", None)
        self._requested_action = getattr(action_type, "NONE", None)

    @abstractmethod
    def load(self) -> None:
        """Load the model and related components."""

    @abstractmethod
    def unload(self) -> None:
        """Unload the model and free resources."""

    @property
    def device_index(self) -> int:
        """Return the configured device index for this model type."""
        device = self._device_override()
        if device is not None:
            return int(device)
        field_name = self._memory_settings_field()
        return int(getattr(self.memory_settings, field_name))

    def _device_override(self) -> Optional[str]:
        """Return one environment override for the current model type."""
        return {
            "LLM": AIRUNNER_MEM_LLM_DEVICE,
            "SD": AIRUNNER_MEM_SD_DEVICE,
            "STT": AIRUNNER_MEM_STT_DEVICE,
            "TTS": AIRUNNER_MEM_TTS_DEVICE,
        }.get(self._model_type_name())

    def _memory_settings_field(self) -> str:
        """Return the memory-settings device field for the model type."""
        return {
            "LLM": "default_gpu_llm",
            "SD": "default_gpu_sd",
            "STT": "default_gpu_stt",
            "TTS": "default_gpu_tts",
        }[self._model_type_name()]

    def _model_type_name(self) -> str:
        """Return the current model type name across enum variants."""
        if self.model_type is None:
            raise ValueError("model_type not set")
        return getattr(self.model_type, "name", str(self.model_type))

    @property
    def device(self) -> torch.device:
        """Return the torch device used for loading and cleanup."""
        return get_torch_device(self.device_index)

    @property
    def attn_implementation(self) -> str:
        """Return the attention implementation for transformer models."""
        enabled = getattr(self, "enabled_backends", [])
        if flash_attn_func and "flash" in enabled:
            if is_ampere_or_newer(self.device_index):
                return "flash_attention_2"
        return "sdpa"

    @property
    def llm_dtype(self) -> Any:
        """Return the persisted LLM dtype setting."""
        return self.llm_generator_settings.dtype

    @property
    def use_cuda(self) -> bool:
        """Return whether CUDA should be used for this manager."""
        if self.handler_type == "transformer":
            if self.llm_dtype == "32bit" or not self.use_gpu:
                return False
        return self.application_settings.use_cuda and torch.cuda.is_available()

    @property
    def cuda_index(self) -> int:
        """Return the default CUDA card index."""
        return 0

    @property
    def torch_dtype(self) -> torch.dtype:
        """Return the preferred torch dtype for model loading."""
        return torch.float16 if self.use_cuda else torch.float32

    def change_model_status(self, model: Any, status: Any) -> None:
        """Update one tracked model status and notify the API when present."""
        if model not in self._model_status:
            model_name = getattr(model, "name", model)
            self.logger.warning(
                "Instance %s attempted to change undefined model type %s",
                id(self),
                model_name,
            )
            return
        self._model_status[model] = status
        api = peek_registered_api()
        callback = getattr(api, "change_model_status", None)
        if callable(callback):
            try:
                callback(model, status)
            except Exception:
                self.logger.debug(
                    "Ignoring model-status callback failure for %s",
                    getattr(model, "name", model),
                )


__all__ = ["BaseModelManager"]