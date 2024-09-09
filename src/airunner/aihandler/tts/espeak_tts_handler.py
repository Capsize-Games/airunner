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
        print("USING ESPEAK", message, rate, volume, pitch, voice)

        self.engine.setProperty('rate', 100.0)
        self.engine.setProperty('volume', 100.0 / 100.0)
        self.engine.setProperty('pitch', 100.0)
        self.engine.setProperty('voice', f'{voice}')
        self.engine.say(message)
        self.engine.runAndWait()

    def run(self):
        if self.engine is None:
            self.logger.debug("Initializing espeak")
            self.engine = pyttsx3.init()
        super().run()

    def load(self, target_model=None):
        super().load(target_model)
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED, self.model_path)
