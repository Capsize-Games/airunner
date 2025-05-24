# Device management logic for model managers
from airunner.enums import ModelType
from airunner.settings import (
    AIRUNNER_MEM_LLM_DEVICE,
    AIRUNNER_MEM_SD_DEVICE,
    AIRUNNER_MEM_TTS_DEVICE,
    AIRUNNER_MEM_STT_DEVICE,
)


class DeviceManagerMixin:
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
