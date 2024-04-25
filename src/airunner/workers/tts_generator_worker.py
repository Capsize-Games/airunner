import queue

from PySide6.QtCore import QThread

from airunner.aihandler.tts.bark_tts_handler import BarkTTSHandler
from airunner.aihandler.tts.espeak_tts_handler import EspeakTTSHandler
from airunner.aihandler.tts.speecht5_tts_handler import SpeechT5TTSHandler
from airunner.enums import SignalCode, QueueType, TTSModel
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker
from airunner.aihandler.tts.espeak_tts_handler import EspeakTTSHandler


class TTSGeneratorWorker(Worker):
    """
    Takes input text from any source and generates speech from it using the TTS class.
    """
    tokens = []

    def __init__(self, *args, **kwargs):
        tts_model = self.settings["tts_settings"]["tts_model"]
        if tts_model == TTSModel.ESPEAK:
            tts_handler_class_ = EspeakTTSHandler
        elif tts_model == TTSModel.SPEECHT5:
            tts_handler_class_ = SpeechT5TTSHandler
        elif tts_model == TTSModel.BARK:
            tts_handler_class_ = BarkTTSHandler
        super().__init__(*args, **kwargs)
        self.tts = tts_handler_class_()
        self.tts.run()
        self.play_queue = []
        self.play_queue_started = False
        self.do_interrupt = False
        self.register(SignalCode.INTERRUPT_PROCESS_SIGNAL, self.on_interrupt_process_signal)
        self.register(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL, self.on_unblock_tts_generator_signal)

    def add_to_queue(self, message):
        if self.do_interrupt:
            return
        super().add_to_queue(message)
    
    def run(self):
        if self.queue_type == QueueType.NONE:
            return
        self.logger.debug("Starting")
        self.running = True
        while self.running:
            self.preprocess()
            try:
                msg = self.get_item_from_queue()
                if msg is not None:
                    self.handle_message(msg)
            except queue.Empty:
                msg = None
            if self.paused:
                self.logger.debug("Paused")
                while self.paused:
                    QThread.msleep(SLEEP_TIME_IN_MS)
                self.logger.debug("Resumed")
            QThread.msleep(SLEEP_TIME_IN_MS)

    def get_item_from_queue(self):
        if self.do_interrupt:
            return None
        return super().get_item_from_queue()

    def on_interrupt_process_signal(self, _message: dict):
        self.play_queue = []
        self.play_queue_started = False
        self.tokens = []
        self.queue = queue.Queue()
        self.do_interrupt = True
        self.paused = True

    def on_unblock_tts_generator_signal(self, _ignore: dict):
        self.logger.debug("Unblocking TTS generation...")
        self.do_interrupt = False
        self.paused = False

    def handle_message(self, data):
        if self.do_interrupt:
            return

        # Add the incoming tokens to the list
        self.logger.debug("Adding tokens to list...")
        self.tokens.extend(data["message"])
        finalize = data.get("finalize", False)

        # Convert the tokens to a string
        text = "".join(self.tokens)

        if finalize:
            self.generate(text)
            self.play_queue_started = True
            self.tokens = []
        else:
            # Split text at punctuation
            if self.tts.target_model == "bark":
                punctuation = ["\n"]
            else:
                punctuation = [".", "?", "!", ";", ":", "\n", ","]

            for p in punctuation:
                if self.do_interrupt:
                    return
                text = text.strip()
                if p in text:
                    split_text = text.split(p, 1)  # Split at the first occurrence of punctuation
                    if len(split_text) > 1:
                        sentence = split_text[0]
                        self.generate(sentence)
                        self.play_queue_started = True

                        # Convert the remaining string back to a list of tokens
                        remaining_text = split_text[1].strip()
                        if not self.do_interrupt:
                            self.tokens = list(remaining_text)
                            break
        if self.do_interrupt:
            self.on_interrupt_process_signal({})

    def generate(self, message):
        if self.do_interrupt:
            return

        self.logger.debug("Generating TTS...")

        if type(message) == dict:
            message = message.get("message", "")
        
        self.logger.debug(message)
        
        response = self.tts.generate(message)

        if self.do_interrupt:
            return

        if response is not None:
            self.emit_signal(
                SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
                {
                    "message": response
                }
            )
