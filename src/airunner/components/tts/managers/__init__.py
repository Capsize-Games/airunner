__all__ = [
    "TTSModelManager",
    "SpeechT5ModelManager",
    "OpenVoiceModelManager",
    "EspeakModelManager",
]


def __getattr__(name):
    if name == "TTSModelManager":
        from airunner.components.tts.managers.tts_model_manager import TTSModelManager

        return TTSModelManager
    elif name == "SpeechT5ModelManager":
        from airunner.components.tts.managers.speecht5_model_manager import SpeechT5ModelManager

        return SpeechT5ModelManager
    elif name == "OpenVoiceModelManager":
        from airunner.components.tts.managers.openvoice_model_manager import OpenVoiceModelManager

        return OpenVoiceModelManager
    elif name == "EspeakModelManager":
        from airunner.components.tts.managers.espeak_model_manager import EspeakModelManager

        return EspeakModelManager
    raise AttributeError(f"module {__name__} has no attribute {name}")
