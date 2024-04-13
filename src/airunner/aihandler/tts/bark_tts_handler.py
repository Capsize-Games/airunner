import time
from transformers import BarkModel, BarkProcessor
from airunner.aihandler.tts.tts_handler import TTSHandler


class BarkTTSHandler(TTSHandler):
    target_model = "bark"
    model_class_ = BarkModel
    processor_class_ = BarkProcessor

    @property
    def processor_path(self):
        return self.settings["tts_settings"]["bark"]["processor_path"]

    @property
    def model_path(self):
        return self.settings["tts_settings"]["bark"]["model_path"]

    def load_model(self):
        super().load_model()

        self.model = self.model.to_bettertransformer()
        self.model.enable_cpu_offload()

    def do_generate(self, message):
        self.logger.debug("Generating TTS with Bark...")
        self.logger.debug("Processing inputs...")
        settings = self.settings["tts_settings"]["bark"]
        inputs = self.processor(
            text=message,
            voice_preset=settings["voice"]
        )
        inputs = self.move_inputs_to_device(inputs)

        self.logger.debug("Generating speech...")
        start = time.time()
        params = {
            **inputs,
            'fine_temperature': settings["fine_temperature"] / 100.0,
            'coarse_temperature': settings["coarse_temperature"] / 100.0,
            'semantic_temperature': settings["semantic_temperature"] / 100.0,
        }

        speech = self.model.generate(**params)
        if not self.cancel_generated_speech:
            self.logger.debug("Generated speech in " + str(time.time() - start) + " seconds")
            response = speech[0].cpu().float().numpy()
            return response
        if not self.do_interrupt:
            self.cancel_generated_speech = False
        return None
