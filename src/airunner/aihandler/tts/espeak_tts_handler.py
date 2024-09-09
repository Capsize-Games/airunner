import pyttsx3
from airunner.aihandler.tts.tts_handler import TTSHandler
from airunner.enums import ModelType, ModelStatus


class EspeakTTSHandler(TTSHandler):
    def do_generate(self, message):
        message = message.replace('"', "'")
        settings = self.settings["tts_settings"]["espeak"]
        rate = settings["rate"]
        pitch = settings["pitch"]
        volume = settings["volume"]
        voice = settings["voice"]
        language = settings["language"]
        gender = settings["gender"]

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
