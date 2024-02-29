import re
import time

from airunner.enums import SignalCode
from airunner.workers.worker import Worker
from airunner.aihandler.tts_handler import TTSHandler


class TTSGeneratorWorker(Worker):
    """
    Takes input text from any source and generates speech from it using the TTS class.
    """
    tokens = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tts = TTSHandler()
        self.tts.run()
        self.play_queue = []
        self.play_queue_started = False

    def handle_message(self, data):
        # Add the incoming tokens to the list
        self.tokens.extend(data["message"])

        # Convert the tokens to a string
        text = "".join(self.tokens).strip()

        # Split text at punctuation
        punctuation = [".", "?", "!", ",", ";", ":"]
        for p in punctuation:
            if p in text:
                split_text = text.split(p, 1)  # Split at the first occurrence of punctuation
                if len(split_text) > 1:
                    sentence = split_text[0]
                    self.generate(sentence)
                    self.play_queue_started = True

                    # Convert the remaining string back to a list of tokens
                    remaining_text = split_text[1].strip()
                    self.tokens = list(remaining_text)
                    break

    def generate(self, message):
        self.logger.info("Generating TTS...")

        if type(message) == dict:
            message = message.get("message", "")
        
        self.logger.info(message)
        
        response = self.tts.generate(message)
        if response is not None:
            self.emit(
                SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
                response
            )
