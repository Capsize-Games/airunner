from abc import ABC

import pyttsx3
from airunner.handlers.tts.tts_handler import TTSHandler
from airunner.enums import ModelType, ModelStatus, Gender


class EspeakHandler(TTSHandler, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rate = None
        self._pitch = None
        self._volume = None
        self._voice = None
        self._language = None
        self._gender = None

    def generate(self, message:str):
        message = message.replace('"', "'")
        if message != "":
            self._engine.say(message)
            self._engine.runAndWait()
        return None

    def load(self, target_model=None):
        self.logger.debug("Initializing espeak")
        self.unload()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self._engine = pyttsx3.init()
        self._initialize()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)

    def unload(self):
        self.logger.debug("Unloading espeak")
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self._engine = None
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)

    def unblock_tts_generator_signal(self):
        pass

    def interrupt_process_signal(self):
        pass

    def _initialize(self):
        self._rate = self.espeak_settings.rate
        self._pitch = self.espeak_settings.pitch
        self._volume = self.espeak_settings.volume
        self._voice = self.espeak_settings.voice
        self._language = self.espeak_settings.language
        gender = self.espeak_settings.gender
        if gender != self.espeak_settings.gender:
            self._gender = gender
            self._engine.setProperty(
                'gender',
                Gender(self._gender)
            )
        self._engine.setProperty('rate', float(self._rate))
        self._engine.setProperty('volume', self._volume / 100.0)
        self._engine.setProperty('pitch', float(self._pitch))
        self._engine.setProperty('voice', f'{self._voice}')
        self._engine.setProperty('language', self._language)
