import re
import time

from airunner.enums import SignalCode
from airunner.workers.worker import Worker
from airunner.aihandler.tts_handler import TTSHandler


class TTSGeneratorWorker(Worker):
    """
    Takes input text from any source and generates speech from it using the TTS class.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tts = TTSHandler()
        self.tts.run()
        self.play_queue = []
        self.play_queue_started = False

    tokens = []
    def handle_message(self, data):
        # Add the incoming tokens to the list
        self.tokens.extend(data["message"])

        # Convert the tokens to a string
        text = "".join(self.tokens).strip()

        # Split text at punctuation
        punctuation = [".", "?", "!"]
        for p in punctuation:
            if p in text:
                split_text = text.split(p, 1)  # Split at the first occurrence of punctuation
                if len(split_text) > 1:
                    sentence = split_text[0]
                    print(f"SENTENCE: {sentence}")
                    self.generate(sentence)
                    self.play_queue_started = True

                    # Convert the remaining string back to a list of tokens
                    remaining_text = split_text[1].strip()
                    self.tokens = list(remaining_text)
                    break

    def trim_sentence(self, sentence):
        return re.sub(' +', ' ', sentence.replace("\n", "").strip())

    def generate(self, message):
        self.logger.info("Generating TTS...")

        if type(message) == dict:
            message = message.get("message", "")
        
        self.logger.info(message)
        
        if self.settings["tts_settings"]["use_bark"]:
            response = self.generate_with_bark(message)
        else:
            response = self.generate_with_t5(message)

        self.emit(SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL, response)
    
    def move_inputs_to_device(self, inputs):
        use_cuda = self.settings["tts_settings"]["use_cuda"]
        if use_cuda:
            self.logger.info("Moving inputs to CUDA")
            try:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            except AttributeError:
                pass
        return inputs

    def generate_with_bark(self, text):
        self.logger.info("Generating TTS with Bark...")
        text = text.replace("\n", " ").strip()
        
        self.logger.info("Processing inputs...")
        inputs = self.tts.processor(
            text=text,
            voice_preset=self.settings["tts_settings"]["voice"]
        ).to(self.tts.device)
        inputs = self.move_inputs_to_device(inputs)

        self.logger.info("Generating speech...")
        start = time.time()
        params = dict(
            **inputs, 
            fine_temperature=self.settings["tts_settings"]["fine_temperature"] / 100.0,
            coarse_temperature=self.settings["tts_settings"]["coarse_temperature"] / 100.0,
            semantic_temperature=self.settings["tts_settings"]["semantic_temperature"] / 100.0,
        )
        speech = self.tts.model.generate(**params)
        self.logger.info("Generated speech in " + str(time.time() - start) + " seconds")

        response = speech[0].cpu().float().numpy()
        return response
    
    def generate_with_t5(self, text):
        self.logger.info("Generating TTS with SpeechT5...")
        text = text.replace("\n", " ").strip()
        
        self.logger.info("Processing inputs...")

        inputs = self.tts.processor(text=text, return_tensors="pt")
        inputs = self.move_inputs_to_device(inputs)

        self.logger.info("Generating speech...")
        start = time.time()
        params = dict(
            **inputs,
            speaker_embeddings=self.tts.speaker_embeddings,
            vocoder=self.tts.vocoder,
            max_length=100,
        )
        speech = self.tts.model.generate(**params)
        self.logger.info("Generated speech in " + str(time.time() - start) + " seconds")
        response = speech.cpu().float().numpy()
        return response
