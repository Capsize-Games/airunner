__all__ = [
    "TTSModelManager",
    "SpeechT5ModelManager",
    "OpenVoiceModelManager",
    "EspeakModelManager",
]


def __getattr__(name):
    if name == "TTSModelManager":
        from .tts_model_manager import TTSModelManager

        return TTSModelManager
    elif name == "SpeechT5ModelManager":
        from .speecht5_model_manager import SpeechT5ModelManager

        return SpeechT5ModelManager
    elif name == "OpenVoiceModelManager":
        from .openvoice_model_manager import OpenVoiceModelManager

        return OpenVoiceModelManager
    elif name == "EspeakModelManager":
        from .espeak_model_manager import EspeakModelManager

        return EspeakModelManager
    raise AttributeError(f"module {__name__} has no attribute {name}")
