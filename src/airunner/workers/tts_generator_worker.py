import queue
import threading

from PySide6.QtCore import QThread

from airunner.enums import SignalCode, QueueType, TTSModel
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker


class TTSGeneratorWorker(Worker):
    """
    Takes input text from any source and generates speech from it using the TTS class.
    """
    tokens = []

    def __init__(self, *args, **kwargs):
        self.signals = {
            (SignalCode.INTERRUPT_PROCESS_SIGNAL, self.on_interrupt_process_signal),
            (SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL, self.on_unblock_tts_generator_signal),
            # (SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal),
            (SignalCode.TTS_ENABLE_SIGNAL, self.on_enable_tts_signal),
            (SignalCode.TTS_DISABLE_SIGNAL, self.on_disable_tts_signal),
            (SignalCode.TTS_LOAD_SIGNAL, self.on_tts_load_signal),
            (SignalCode.TTS_UNLOAD_SIGNAL, self.on_tts_unload_signal),
            (SignalCode.TTS_PROCESSOR_LOAD_SIGNAL, self.on_tts_processor_load_signal),
            (SignalCode.TTS_PROCESSOR_UNLOAD_SIGNAL, self.on_tts_processor_unload_signal),
            (SignalCode.TTS_VOCODER_LOAD_SIGNAL, self.on_tts_vocoder_load_signal),
            (SignalCode.TTS_VOCODER_UNLOAD_SIGNAL, self.on_tts_vocoder_unload_signal),
            (SignalCode.TTS_SPEAKER_EMBEDDINGS_LOAD_SIGNAL, self.on_tts_speaker_embeddings_load_signal),
            (SignalCode.TTS_SPEAKER_EMBEDDINGS_UNLOAD_SIGNAL, self.on_tts_speaker_embeddings_unload_signal),
            (SignalCode.TTS_TOKENIZER_LOAD_SIGNAL, self.on_tts_tokenizer_load_signal),
            (SignalCode.TTS_TOKENIZER_UNLOAD_SIGNAL, self.on_tts_tokenizer_unload_signal),
            (SignalCode.TTS_DATASET_LOAD_SIGNAL, self.on_dataset_tts_load_signal),
            (SignalCode.TTS_DATASET_UNLOAD_SIGNAL, self.on_dataset_tts_unload_signal),
            (SignalCode.TTS_FEATURE_EXTRACTOR_LOAD_SIGNAL, self.on_tts_feature_extractor_load_signal),
            (SignalCode.TTS_FEATURE_EXTRACTOR_UNLOAD_SIGNAL, self.on_tts_feature_extractor_unload_signal),
        }
        self.tts = None
        self.play_queue = []
        self.play_queue_started = False
        self.do_interrupt = False
        super().__init__(*args, **kwargs)

    def on_enable_tts_signal(self):
        if self.tts:
            self.tts.enable_tts_signal()

    def on_disable_tts_signal(self):
        if self.tts:
            self.tts.disable_tts_signal()

    def on_tts_load_signal(self, message: dict):
        if self.tts:
            self.tts.tts_load_signal(message)

    def on_tts_unload_signal(self, message: dict):
        if self.tts:
            self.tts.tts_unload_signal(message)

    def on_tts_processor_load_signal(self, message: dict):
        if self.tts:
            self.tts.tts_processor_load_signal(message)

    def on_tts_processor_unload_signal(self, message: dict):
        if self.tts:
            self.tts.tts_processor_unload_signal(message)

    def on_tts_vocoder_load_signal(self, message: dict):
        if self.tts:
            self.tts.tts_vocoder_load_signal(message)

    def on_tts_vocoder_unload_signal(self, message: dict):
        if self.tts:
            self.tts.tts_vocoder_unload_signal(message)

    def on_tts_speaker_embeddings_load_signal(self, message: dict):
        if self.tts:
            self.tts.tts_speaker_embeddings_load_signal(message)

    def on_tts_speaker_embeddings_unload_signal(self, message: dict):
        if self.tts:
            self.tts.tts_speaker_embeddings_unload_signal(message)

    def on_tts_tokenizer_load_signal(self, message: dict):
        if self.tts:
            self.tts.tts_tokenizer_load_signal(message)

    def on_tts_tokenizer_unload_signal(self, message: dict):
        if self.tts:
            self.tts.tts_tokenizer_unload_signal(message)

    def on_dataset_tts_load_signal(self, message: dict):
        if self.tts:
            self.tts.dataset_tts_load_signal(message)

    def on_dataset_tts_unload_signal(self, message: dict):
        if self.tts:
            self.tts.dataset_tts_unload_signal(message)

    def on_tts_feature_extractor_load_signal(self, message: dict):
        if self.tts:
            self.tts.tts_feature_extractor_load_signal(message)

    def on_tts_feature_extractor_unload_signal(self, message: dict):
        if self.tts:
            self.tts.tts_feature_extractor_unload_signal(message)

    def on_interrupt_process_signal(self):
        if self.tts:
            self.tts.interrupt_process_signal()

    def on_unblock_tts_generator_signal(self, message):
        if self.tts:
            self.tts.unblock_tts_generator_signal(message)


    def on_application_settings_changed_signal(self, message: dict):
        if self.tts:
            self.tts.application_settings_changed_signal(message)

    def start_worker_thread(self):
        tts_model = self.tts_settings.model.lower()

        if tts_model == TTSModel.ESPEAK.value:
            from airunner.aihandler.tts.espeak_tts_handler import EspeakTTSHandler
            tts_handler_class_ = EspeakTTSHandler
        elif tts_model == TTSModel.SPEECHT5.value:
            from airunner.aihandler.tts.speecht5_tts_handler import SpeechT5TTSHandler
            tts_handler_class_ = SpeechT5TTSHandler
        elif tts_model == TTSModel.BARK.value:
            from airunner.aihandler.tts.bark_tts_handler import BarkTTSHandler
            tts_handler_class_ = BarkTTSHandler
        self.tts = tts_handler_class_()
        self.tts.run()

    def add_to_queue(self, message):
        if self.do_interrupt:
            return
        super().add_to_queue(message)
    
    def run(self):
        if self.queue_type == QueueType.NONE:
            return
        self.logger.debug("Starting TTS generator worker")
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

    def on_interrupt_process_signal(self):
        self.play_queue = []
        self.play_queue_started = False
        self.tokens = []
        self.queue = queue.Queue()
        self.do_interrupt = True
        self.paused = True

    def on_unblock_tts_generator_signal(self):
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
            self.on_interrupt_process_signal()

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

