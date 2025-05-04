import queue
import re
from typing import Optional, Type, Dict

from airunner.settings import AIRUNNER_TTS_MODEL_TYPE
from airunner.enums import (
    SignalCode,
    TTSModel,
    ModelStatus,
    LLMActionType,
    QueueType,
)
from airunner.workers.worker import Worker
from airunner.settings import AIRUNNER_TTS_ON, AIRUNNER_ENABLE_OPEN_VOICE
from airunner.handlers.tts.tts_request import (
    OpenVoiceTTSRequest,
    TTSRequest,
    EspeakTTSRequest,
)


class TTSGeneratorWorker(Worker):
    """
    Takes input text from any source and generates speech from it using the TTS class.
    """

    tokens = []
    queue_type = QueueType.GET_NEXT_ITEM

    def __init__(self, *args, **kwargs):
        self.tts = None
        self.play_queue = []
        self.play_queue_started = False
        self.do_interrupt = False
        self._current_model: Optional[str] = None
        self.signal_handlers = {
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.on_interrupt_process_signal,
            SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL: self.on_unblock_tts_generator_signal,
            SignalCode.TTS_ENABLE_SIGNAL: self.on_enable_tts_signal,
            SignalCode.TTS_DISABLE_SIGNAL: self.on_disable_tts_signal,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_llm_text_streamed_signal,
            SignalCode.TTS_MODEL_CHANGED: self._reload_tts_model_manager,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
        }
        super().__init__()

    @property
    def tts_enabled(self) -> bool:
        return (
            self.application_settings and self.application_settings.tts_enabled
        ) or AIRUNNER_TTS_ON

    def on_llm_text_streamed_signal(self, data):
        if not self.tts_enabled:
            return
        response = data.get("response", None)

        if not response:
            raise ValueError("No LLMResponse object found in data")

        if response.action is LLMActionType.GENERATE_IMAGE:
            return

        # Initialize TTS if needed but avoid reloading if it's already in the process
        if not self.tts or (
            self.tts
            and not self.tts.model_status
            not in [ModelStatus.LOADED, ModelStatus.LOADING]
        ):
            self._load_tts()
        elif self.do_interrupt and response and response.is_first_message:
            self.on_unblock_tts_generator_signal()

        self.add_to_queue(
            {
                "message": response.message.replace("</s>", "")
                + ("." if response.is_end_of_message else ""),
                "is_end_of_message": response.is_end_of_message,
            }
        )

    def on_interrupt_process_signal(self):
        if self.tts:
            self.play_queue = []
            self.play_queue_started = False
            self.tokens = []
            self.queue = queue.Queue()
            self.do_interrupt = True
            self.paused = True
            self.tts.interrupt_process_signal()

    def on_unblock_tts_generator_signal(self, data: Optional[Dict]):
        if self.tts_enabled:
            self.logger.debug("Unblocking TTS generation...")
            self.do_interrupt = False
            self.paused = False
            self.tts.unblock_tts_generator_signal()
        if data is not None:
            callback = data.get("callback", None)
            if callback is not None:
                callback()

    def on_enable_tts_signal(self):
        self._load_tts()

    def on_disable_tts_signal(self):
        self._unload_tts()

    def start_worker_thread(self):
        if self.tts_enabled:
            self._load_tts()

    def _reload_tts_model_manager(self, data: dict):
        self.logger.info("Reloading TTS handler...")
        self.logger.info(
            f"Current model: {self._current_model} | New model: {data['model']}"
        )
        if self._current_model != data["model"]:
            self._current_model = data["model"]
            self.tts.unload()
            self._load_tts()

    def on_application_settings_changed_signal(self, data):
        if (
            data
            and data.get("setting_name", "") == "speech_t5_settings"
            and data.get("column_name", "") == "voice"
        ):
            self.tts.reload_speaker_embeddings()

    def _initialize_tts_model_manager(self):
        self.logger.info("Initializing TTS handler...")
        model = (
            AIRUNNER_TTS_MODEL_TYPE or self.chatbot_voice_settings.model_type
        )
        if model is None:
            self.logger.error("No TTS model found. Skipping initialization.")
            return
        model_type = TTSModel(model)
        # Only re-instantiate if model type changed or tts is None
        if self.tts and self._current_model == model:
            self.logger.debug(
                "TTS model already initialized and matches current model."
            )
            return
        self._current_model = model
        if model_type is TTSModel.SPEECHT5:
            from airunner.handlers.tts.speecht5_model_manager import (
                SpeechT5ModelManager,
            )

            tts_model_manager_class_ = SpeechT5ModelManager
        elif AIRUNNER_ENABLE_OPEN_VOICE and model_type is TTSModel.OPENVOICE:
            from airunner.handlers.tts.openvoice_model_manager import (
                OpenVoiceModelManager,
            )

            tts_model_manager_class_ = OpenVoiceModelManager
        else:
            from airunner.handlers.tts.espeak_model_manager import (
                EspeakModelManager,
            )

            tts_model_manager_class_ = EspeakModelManager
        self.tts = tts_model_manager_class_()
        self.logger.debug(f"Instantiated new TTS model manager: {self.tts}")

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

        message = data.get("message", "")
        is_end_of_message = data.get("is_end_of_message", False)

        # Add the incoming message to the tokens list
        if isinstance(message, str):
            self.tokens.append(message)
        else:
            self.tokens.extend(message)

        # Convert the tokens to a string
        text = "".join(self.tokens)

        # Regular expression to match timestamps in the format HH:MM
        timestamp_pattern = re.compile(r"\b(\d{1,2}):(\d{2})\b")

        # Replace the colon in the matched timestamps with a space
        text = timestamp_pattern.sub(r"\1 \2", text)

        def word_count(s):
            return len(s.split())

        if is_end_of_message:
            # If this is the end of a message, generate the full text and clear tokens
            self._generate(text)
            self.play_queue_started = True
            self.tokens = []
        else:
            # Split text at punctuation for incremental TTS
            punctuation = [".", "?", "!", ";", ":", "\n", ","]
            for p in punctuation:
                if self.do_interrupt:
                    return
                text = text.strip()
                if p in text:
                    split_text = text.split(
                        p, 1
                    )  # Split at the first occurrence of punctuation
                    if len(split_text) > 1:
                        before, after = split_text[0], split_text[1]
                        if p == ",":
                            if word_count(before) < 3 or word_count(after) < 3:
                                continue  # Skip splitting if there are not enough words around the comma
                        sentence = (
                            before + p
                        )  # Include the punctuation in the sentence
                        self._generate(sentence)
                        self.play_queue_started = True

                        # Set tokens to the remaining text
                        remaining_text = after.strip()
                        if not self.do_interrupt:
                            self.tokens = (
                                [remaining_text] if remaining_text else []
                            )
                            break

        if self.do_interrupt:
            self.on_interrupt_process_signal()

    def _load_tts(self):
        if not self.tts_enabled:
            self.logger.info("TTS is disabled. Skipping load.")
            return

        if not self.tts:
            self._initialize_tts_model_manager()

        if self.tts:
            self.tts.load()

    def load(self):
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

        model = (
            AIRUNNER_TTS_MODEL_TYPE or self.chatbot_voice_settings.model_type
        )

        if model is None:
            self.logger.error("No TTS model found. Skipping generation.")
            return

        model_type = TTSModel(model)

        self.logger.debug(f"self.tts: {self.tts} | model_type: {model_type}")

        response = None
        if self.tts:
            tts_req: Optional[Type[TTSRequest]] = None

            if model_type is TTSModel.SPEECHT5:
                tts_req = TTSRequest(
                    message=message, gender=self.chatbot.gender
                )
            elif (
                AIRUNNER_ENABLE_OPEN_VOICE and model_type is TTSModel.OPENVOICE
            ):
                tts_req = OpenVoiceTTSRequest(
                    message=message, gender=self.chatbot.gender
                )
            else:
                tts_req = EspeakTTSRequest(
                    message=message,
                    gender=self.chatbot.gender,
                    rate=self.espeak_settings.rate,
                    pitch=self.espeak_settings.pitch,
                    volume=self.espeak_settings.volume,
                    voice=self.espeak_settings.voice,
                    language=self.espeak_settings.language,
                )

            if tts_req:
                response = self.tts.generate(tts_req)

        if self.do_interrupt:
            return

        if response is not None:
            self.emit_signal(
                SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
                {"message": response},
            )
