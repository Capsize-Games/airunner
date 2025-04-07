__all__ = [
    "BaseModelManager",
    "LLMModelManager",
    "TTSModelManager",
    "SpeechT5ModelManager",
    "OpenVoiceModelManager",
    "EspeakModelManager",
    "WhisperModelManager",
    "StableDiffusionModelManager",
]


def __getattr__(name):
    if name == "BaseModelManager":
        from .base_model_manager import BaseModelManager

        return BaseModelManager
    elif name == "LLMModelManager":
        from .llm.llm_model_manager import LLMModelManager

        return LLMModelManager
    elif name == "TTSModelManager":
        from .tts.tts_model_manager import TTSModelManager

        return TTSModelManager
    elif name == "SpeechT5ModelManager":
        from .tts.speecht5_model_manager import SpeechT5ModelManager

        return SpeechT5ModelManager
    elif name == "OpenVoiceModelManager":
        from .tts.openvoice_model_manager import OpenVoiceModelManager

        return OpenVoiceModelManager
    elif name == "EspeakModelManager":
        from .tts.espeak_model_manager import EspeakModelManager

        return EspeakModelManager
    elif name == "WhisperModelManager":
        from .stt.whisper_model_manager import WhisperModelManager

        return WhisperModelManager
    elif name == "StableDiffusionModelManager":
        from .stablediffusion.stable_diffusion_model_manager import (
            StableDiffusionModelManager,
        )

        return StableDiffusionModelManager
    raise AttributeError(f"module {__name__} has no attribute {name}")
