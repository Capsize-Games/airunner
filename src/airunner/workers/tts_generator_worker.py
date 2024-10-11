import queue
import threading

from airunner.enums import SignalCode, TTSModel, ModelStatus
from airunner.handlers.tts.espeak_tts_handler import EspeakTTSHandler
from airunner.handlers.tts.speecht5_tts_handler import SpeechT5TTSHandler
from airunner.workers.worker import Worker


class TTSGeneratorWorker(Worker):
    """
    Takes input text from any source and generates speech from it using the TTS class.
    """
    tokens = []

    def __init__(self, *args, **kwargs):
        self.tts = None
        self.play_queue = []
        self.play_queue_started = False
        self.do_interrupt = False
        super().__init__(*args, signals=(
            (SignalCode.INTERRUPT_PROCESS_SIGNAL, self.on_interrupt_process_signal),
            (SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL, self.on_unblock_tts_generator_signal),
            (SignalCode.TTS_ENABLE_SIGNAL, self.on_enable_tts_signal),
            (SignalCode.TTS_DISABLE_SIGNAL, self.on_disable_tts_signal),
            (SignalCode.LLM_TEXT_STREAMED_SIGNAL, self.on_llm_text_streamed_signal),
        ), **kwargs)

    def on_llm_text_streamed_signal(self, data):
        if not self.application_settings.tts_enabled:
            return

        if self.tts.model_status is not ModelStatus.LOADED:
            self.tts.load()

        message = data.get("message", "")
        is_end_of_message = data.get("is_end_of_message", False)
        self.add_to_queue({
            'message': message.replace("</s>", "") + ("." if is_end_of_message else ""),
            'tts_settings': self.tts_settings,
            'is_end_of_message': is_end_of_message,
        })

    def on_interrupt_process_signal(self):
        self.play_queue = []
        self.play_queue_started = False
        self.tokens = []
        self.queue = queue.Queue()
        self.do_interrupt = True
        self.paused = True
        self.tts.interrupt_process_signal()

    def on_unblock_tts_generator_signal(self):
        self.logger.debug("Unblocking TTS generation...")
        self.do_interrupt = False
        self.paused = False
        self.tts.unblock_tts_generator_signal()

    def on_enable_tts_signal(self):
        if self.tts:
            thread = threading.Thread(target=self._load_tts)
            thread.start()

    def on_disable_tts_signal(self):
        if self.tts:
            thread = threading.Thread(target=self._unload_tts)
            thread.start()

    def start_worker_thread(self):
        tts_model = self.tts_settings.model.lower()

        if tts_model == TTSModel.ESPEAK.value:
            tts_handler_class_ = EspeakTTSHandler
        else:
            tts_handler_class_ = SpeechT5TTSHandler
        self.tts = tts_handler_class_()
        if self.application_settings.tts_enabled:
            self.tts.load()

    def add_to_queue(self, message):
        if self.do_interrupt:
            return
        super().add_to_queue(message)

    def get_item_from_queue(self):
        if self.do_interrupt:
            return None
        return super().get_item_from_queue()

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
            self._generate(text)
            self.play_queue_started = True
            self.tokens = []
        else:
            # Split text at punctuation
            punctuation = [".", "?", "!", ";", ":", "\n", ","]
            for p in punctuation:
                if self.do_interrupt:
                    return
                text = text.strip()
                if p in text:
                    split_text = text.split(p, 1)  # Split at the first occurrence of punctuation
                    if len(split_text) > 1:
                        sentence = split_text[0]
                        self._generate(sentence)
                        self.play_queue_started = True

                        # Convert the remaining string back to a list of tokens
                        remaining_text = split_text[1].strip()
                        if not self.do_interrupt:
                            self.tokens = list(remaining_text)
                            break
        if self.do_interrupt:
            self.on_interrupt_process_signal()

    def _load_tts(self):
        self.tts.load()

    def _unload_tts(self):
        self.tts.unload()

    def _generate(self, message):
        if self.do_interrupt:
            return
        self.logger.debug("Generating TTS...")

        if type(message) == dict:
            message = message.get("message", "")

        response = None
        if self.tts:
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

