import pyttsx3
from airunner.aihandler.tts.tts_handler import TTSHandler
from airunner.enums import ModelType, ModelStatus, Gender


class EspeakTTSHandler(TTSHandler):
    def do_generate(self, message):
        message = message.replace('"', "'")
        rate = self.espeak_settings.rate
        pitch = self.espeak_settings.pitch
        volume = self.espeak_settings.volume
        voice = self.espeak_settings.voice
        language = self.espeak_settings.language
        gender = Gender(self.espeak_settings.gender)

        self.engine.setProperty('rate', float(rate))
        self.engine.setProperty('volume', volume / 100.0)
        self.engine.setProperty('pitch', float(pitch))
        self.engine.setProperty('voice', f'{voice}')
        self.engine.setProperty('language', language)
        self.engine.setProperty('gender', gender)
        self.engine.say(message)
        self.engine.runAndWait()

    def run(self):
        if self.engine is None:
            self.logger.debug("Initializing espeak")
            self.engine = pyttsx3.init()
        super().run()

    def load_model(self):
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)

    def unload_model(self):
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)
