import queue
import re
import threading
from typing import Optional

from airunner.enums import SignalCode, TTSModel, ModelStatus, LLMActionType
from airunner.handlers.tts.espeak_handler import EspeakHandler
from airunner.handlers.tts.speecht5_handler import SpeechT5Handler
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
        self._current_model: Optional[str] = None
        super().__init__(*args, signals=(
            (SignalCode.INTERRUPT_PROCESS_SIGNAL, self.on_interrupt_process_signal),
            (SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL, self.on_unblock_tts_generator_signal),
            (SignalCode.TTS_ENABLE_SIGNAL, self.on_enable_tts_signal),
            (SignalCode.TTS_DISABLE_SIGNAL, self.on_disable_tts_signal),
            (SignalCode.LLM_TEXT_STREAMED_SIGNAL, self.on_llm_text_streamed_signal),
            (SignalCode.TTS_MODEL_CHANGED, self._reload_tts_handler),
            (SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal),
        ), **kwargs)

    def on_llm_text_streamed_signal(self, data):
        if not self.application_settings.tts_enabled:
            return

        action = data.get("action", LLMActionType.CHAT)
        if action is LLMActionType.GENERATE_IMAGE:
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
        if self.application_settings.tts_enabled:
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
        self._initialize_tts_handler()
        if self.application_settings.tts_enabled:
            self.tts.load()

    def _reload_tts_handler(self, data: dict):
        if not self.application_settings.tts_enabled:
            return

        if self._current_model != data["model"]:
            self._current_model = data["model"]
            self.tts.unload()
            self._initialize_tts_handler()
            self.tts.load()

    def on_application_settings_changed_signal(self, data):
        if data and data.get("setting_name", "") == "speech_t5_settings" and data.get("column_name", "") == "voice":
            self.tts.reload_speaker_embeddings()

    def _initialize_tts_handler(self):
        self.logger.info("Initializing TTS handler...")
        tts_model = self.tts_settings.model.lower()
        print(tts_model, TTSModel.ESPEAK.value, tts_model == TTSModel.ESPEAK.value)
        if tts_model == TTSModel.ESPEAK.value:
            tts_handler_class_ = EspeakHandler
        else:
            tts_handler_class_ = SpeechT5Handler
        self.tts = tts_handler_class_()

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
        self.tokens.extend(data["message"])
        finalize = data.get("finalize", False)

        # Convert the tokens to a string
        text = "".join(self.tokens)

        # Regular expression to match timestamps in the format HH:MM
        timestamp_pattern = re.compile(r'\b(\d{1,2}):(\d{2})\b')

        # Replace the colon in the matched timestamps with a space
        text = timestamp_pattern.sub(r'\1 \2', text)

        def word_count(s):
            return len(s.split())

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
                        before, after = split_text[0], split_text[1]
                        if p == ",":
                            if word_count(before) < 3 or word_count(after) < 3:
                                continue  # Skip splitting if there are not enough words around the comma
                        sentence = before
                        self._generate(sentence)
                        self.play_queue_started = True

                        # Convert the remaining string back to a list of tokens
                        remaining_text = after.strip()
                        if not self.do_interrupt:
                            self.tokens = list(remaining_text)
                            break
        if self.do_interrupt:
            self.on_interrupt_process_signal()

    def _load_tts(self):
        if self.tts:
            self.tts.load()

    def load(self):
        if not self.tts:
            self._initialize_tts_handler()
        self._load_tts()

    def unload(self):
        self._unload_tts()

    def _unload_tts(self):
        if self.tts:
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
            self.emit_signal(SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL, {
                "message": response
            })

