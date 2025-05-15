from typing import Optional
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
        self._tts_request: Optional[TTSRequest] = None
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

    @property
    def status(self) -> ModelStatus:
        """Get the current model status for TTS."""
        return self._model_status.get(ModelType.TTS, ModelStatus.UNLOADED)

    def generate(self, tts_request: TTSRequest):
        """
        Generate speech from the given message.
        """
        if not self._engine or self.status != ModelStatus.LOADED:
            self.logger.warning(
                "TTS engine not available or not loaded. Cannot generate speech."
                f" Current status: {self.status}"
            )
            return None

        self.tts_request = tts_request
        message = tts_request.message.replace('"', "'")
        if message:
            try:
                self._engine.say(message)
                self._engine.runAndWait()
            except Exception as e:
                self.logger.error(f"Error during speech generation: {e}")
                # Optionally, consider changing model status if generation fails repeatedly
                # self.change_model_status(ModelType.TTS, ModelStatus.FAILED)
        return None

    def load(self, target_model=None):
        """
        Load and initialize the Espeak engine.
        """
        # If already loading or loaded, don't attempt to reinitialize
        if self.status in [ModelStatus.LOADING, ModelStatus.LOADED]:
            self.logger.debug(
                f"Espeak engine already in {self.status} state, skipping initialization"
            )
            return

        self.logger.debug(
            f"Initializing espeak (current status: {self.status})"
        )
        # Don't call unload() here as it triggers the cycle
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        try:
            self._engine = pyttsx3.init()
            self._initialize()
            self.logger.debug(
                f"Espeak engine initialization complete, status: {self.status}"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize espeak: {e}")
            self._engine = None
            self.change_model_status(ModelType.TTS, ModelStatus.FAILED)

    def unload(self):
        """
        Unload the Espeak engine and release resources.
        """
        # If already unloading or unloaded, don't try again
        if self.model_status in [ModelStatus.UNLOADED]:
            return

        self.logger.debug("Unloading espeak")
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)
        self._engine = None
        # No need to change status again after setting it to UNLOADED

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
        if not self._engine:
            self.logger.error(
                "Engine not initialized before calling _initialize"
            )
            return

        try:
            # Configure basic properties first
            rate_to_set = self.rate
            volume_to_set = self.volume
            pitch_to_set = self.pitch

            self._engine.setProperty("rate", float(rate_to_set))
            self._engine.setProperty("volume", volume_to_set / 100.0)
            self._engine.setProperty("pitch", float(pitch_to_set))

            # Get all available voices
            available_voices = self._engine.getProperty("voices")
            if not available_voices:
                self.logger.warning(
                    "No voices available in the pyttsx3 engine"
                )
                return

            # Log available voices for debugging
            voice_ids = [voice.id for voice in available_voices]
            self.logger.debug(f"Available voices: {voice_ids}")

            # Get desired voice/language settings
            language_to_set = self.espeak_settings.voice.lower()
            gender_to_set = self.gender

            # Default voice (first available)
            selected_voice = available_voices[0]

            # Try to find a matching voice by language
            for voice in available_voices:
                # Voice IDs in pyttsx3+espeak often contain the language code
                if language_to_set in voice.id.lower():
                    selected_voice = voice
                    # If we also want to match gender and it's in the ID
                    if (
                        gender_to_set == Gender.FEMALE.value
                        and "female" in voice.id.lower()
                    ):
                        break  # Perfect match
                    elif (
                        gender_to_set == Gender.MALE.value
                        and "male" in voice.id.lower()
                    ):
                        break  # Perfect match

            # Set the selected voice
            self.logger.debug(f"Selected voice: {selected_voice.id}")
            self._engine.setProperty("voice", selected_voice.id)

            self.change_model_status(ModelType.TTS, ModelStatus.LOADED)

        except Exception as e:
            self.logger.error(
                f"Error initializing espeak engine properties: {e}"
            )
            self.change_model_status(ModelType.TTS, ModelStatus.FAILED)
