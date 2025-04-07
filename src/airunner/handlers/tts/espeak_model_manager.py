from typing import Optional, Type
from abc import ABCMeta
import pyttsx3

from airunner.handlers.tts.tts_model_manager import TTSModelManager
from airunner.enums import ModelType, ModelStatus, Gender
from airunner.handlers.tts.tts_request import TTSRequest
from airunner.data.models import EspeakSettings


class EspeakModelManager(TTSModelManager, metaclass=ABCMeta):
    """
    Espeak-based implementation of the TTSModelManager.
    Uses pyttsx3 for text-to-speech generation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tts_request: TTSRequest = None
        self._rate: Optional[int] = None
        self._pitch: Optional[int] = None
        self._volume: Optional[int] = None
        self._voice: Optional[str] = None
        self._language: Optional[str] = None

    @property
    def gender(self) -> str:
        gender = super().gender
        return gender if gender != "" else EspeakSettings.gender.default.arg

    @property
    def language(self) -> str:
        if self.tts_request:
            return self.tts_request.language
        return EspeakSettings.language.default.arg

    @property
    def voice(self) -> str:
        if self.tts_request:
            return self.tts_request.voice
        return EspeakSettings.voice.default.arg

    @property
    def volume(self) -> int:
        if self.tts_request:
            return self.tts_request.volume
        return EspeakSettings.volume.default.arg

    @property
    def pitch(self) -> int:
        if self.tts_request:
            return self.tts_request.pitch
        return EspeakSettings.pitch.default.arg

    @property
    def rate(self) -> int:
        if self.tts_request:
            return self.tts_request.rate
        return EspeakSettings.rate.default.arg

    def generate(self, tts_request: Type[TTSRequest]):
        """
        Generate speech from the given message.
        """
        self.tts_request = tts_request
        message = tts_request.message.replace('"', "'")
        if message:
            self._engine.say(message)
            self._engine.runAndWait()
        return None

    def load(self, target_model=None):
        """
        Load and initialize the Espeak engine.
        """
        self.logger.debug("Initializing espeak")
        self.unload()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self._engine = pyttsx3.init()
        self._initialize()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)

    def unload(self):
        """
        Unload the Espeak engine and release resources.
        """
        self.logger.debug("Unloading espeak")
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self._engine = None
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)

    def unblock_tts_generator_signal(self):
        """
        Placeholder for unblocking TTS generator signal.
        """
        pass

    def interrupt_process_signal(self):
        """
        Placeholder for interrupting the TTS process.
        """
        pass

    def _initialize(self):
        """
        Initialize the Espeak engine with settings.
        """
        voice = self.voice
        if self.espeak_settings and self.gender != self.espeak_settings.gender:
            if self.gender == "Male":
                voice = "male1"
            else:
                self.gender == "Female"
                voice = "female1"
        elif not self.espeak_settings:
            self.logger.warning("Espeak settings are not defined.")
        self._engine.setProperty("rate", float(self.rate))
        self._engine.setProperty("volume", self.volume / 100.0)
        self._engine.setProperty("pitch", float(self.pitch))
        self._engine.setProperty("voice", f"{voice}")
        self._engine.setProperty("language", self.language)
