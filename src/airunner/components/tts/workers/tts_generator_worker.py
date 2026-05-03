import io
import queue
import re
from uuid import uuid4
from typing import Optional, Type, Dict

import soundfile as sf

from airunner.components.tts.managers.exceptions import OpenVoiceError
from airunner.settings import AIRUNNER_TTS_MODEL_TYPE
from airunner.enums import (
    SignalCode,
    TTSModel,
    ModelStatus,
    LLMActionType,
    QueueType,
)
from airunner.components.application.workers.worker import Worker
from airunner.settings import AIRUNNER_TTS_ON
from airunner.components.tts.managers.tts_request import (
    OpenVoiceTTSRequest,
    TTSRequest,
    EspeakTTSRequest,
)
from airunner.components.llm.utils.thinking_parser import (
    normalize_thinking_content,
    strip_stored_thinking_prefix,
    strip_thinking_tags,
)
from airunner.components.llm.utils.stream_text import combine_stream_chunks
from airunner.utils.text.formatter_extended import FormatterExtended
from airunner.enums import ModelType


class TTSGeneratorWorker(Worker):
    """
    Takes input text from any source and generates speech from it using the TTS class.
    """

    tokens = []
    queue_type = QueueType.GET_NEXT_ITEM
    
    # Sentence buffering configuration for better prosody
    SENTENCE_BUFFER_SIZE = 2  # Number of sentences to buffer before generating
    MIN_WORDS_FOR_GENERATION = 8  # Minimum words before generating (even with fewer sentences)

    def __init__(self, *args, **kwargs):
        self.tts = None
        self.play_queue = []
        self.play_queue_started = False
        self.do_interrupt = False
        self._current_model: Optional[str] = None
        self._failed_model: Optional[str] = None
        self._sentence_buffer = []  # Buffer to hold complete sentences
        self._active_request_id: Optional[str] = None
        self._reset_llm_stream_state()
        super().__init__()

    def _reset_llm_stream_state(self) -> None:
        """Clear per-response visible/thinking tracking for TTS."""
        self._llm_request_id = None
        self._llm_raw_visible_chunks = []
        self._llm_spoken_visible_text = ""
        self._llm_thinking_active = False
        self._llm_thinking_content = None

    def _sync_llm_stream_state(
        self,
        request_id: Optional[str],
        *,
        is_first_message: bool = False,
    ) -> None:
        """Reset TTS stream state when one new LLM response begins."""
        if not hasattr(self, "_llm_raw_visible_chunks"):
            TTSGeneratorWorker._reset_llm_stream_state(self)

        current_request_id = getattr(self, "_llm_request_id", None)
        same_request = bool(request_id) and request_id == current_request_id
        if (
            request_id and current_request_id and request_id != current_request_id
        ) or (
            is_first_message and not same_request
        ):
            TTSGeneratorWorker._reset_llm_stream_state(self)
            current_request_id = None
        if request_id and current_request_id is None:
            self._llm_request_id = request_id

    def _visible_tts_delta(self) -> str:
        """Return one newly visible reply fragment safe to speak."""
        if getattr(self, "_llm_thinking_active", False):
            return ""

        raw_chunks = getattr(self, "_llm_raw_visible_chunks", [])
        visible_text = strip_stored_thinking_prefix(
            combine_stream_chunks(raw_chunks),
            getattr(self, "_llm_thinking_content", None),
        )
        spoken_text = getattr(self, "_llm_spoken_visible_text", "")

        if not visible_text or visible_text == spoken_text:
            return ""
        if not spoken_text:
            self._llm_spoken_visible_text = visible_text
            return visible_text
        if visible_text.startswith(spoken_text):
            delta = visible_text[len(spoken_text) :]
            self._llm_spoken_visible_text = visible_text
            return delta

        self._llm_spoken_visible_text = visible_text
        return visible_text

    def on_llm_thinking_signal(self, data: Optional[Dict]) -> None:
        """Track active reasoning so TTS only speaks final visible text."""
        if not isinstance(data, dict):
            return

        TTSGeneratorWorker._sync_llm_stream_state(
            self,
            data.get("request_id"),
        )

        status = str(data.get("status", "")).strip().lower()
        if status == "started":
            self._llm_thinking_active = True
            self._llm_thinking_content = None
            return
        if status == "streaming":
            self._llm_thinking_active = True
            return
        if status == "completed":
            self._llm_thinking_active = False
            self._llm_thinking_content = normalize_thinking_content(
                data.get("content")
            )

    @property
    def tts_enabled(self) -> bool:
        return (
            self.application_settings and self.application_settings.tts_enabled
        ) or AIRUNNER_TTS_ON

    def _current_api(self):
        """Return the freshest API reference available to this worker."""
        candidates = []
        refresher = getattr(self, "refresh_api_reference", None)
        if callable(refresher):
            candidates.append(refresher())
        candidates.append(getattr(self, "api", None))
        resolve_api = getattr(
            self,
            "_resolve_api_instance",
            TTSGeneratorWorker._resolve_api_instance,
        )
        candidates.append(resolve_api())
        main_window_getter = getattr(
            self,
            "_main_window",
            TTSGeneratorWorker._main_window,
        )
        candidates.append(main_window_getter())

        fallback_api = None
        for candidate in candidates:
            candidate = TTSGeneratorWorker._normalize_api_candidate(candidate)
            if candidate is None or getattr(candidate, "headless", False):
                continue
            if getattr(candidate, "daemon_client", None) is not None:
                self.api = candidate
                return candidate
            if fallback_api is None:
                fallback_api = candidate

        if fallback_api is not None:
            self.api = fallback_api
        return fallback_api

    @staticmethod
    def _normalize_api_candidate(candidate):
        """Return one app-like API object from a nested candidate."""
        if candidate is None:
            return None

        root_api = getattr(candidate, "api", None)
        if root_api is not None and getattr(candidate, "daemon_client", None) is None:
            return root_api

        app_api = getattr(getattr(candidate, "app", None), "api", None)
        if app_api is not None and getattr(candidate, "daemon_client", None) is None:
            return app_api
        return candidate

    @staticmethod
    def _resolve_api_instance():
        """Resolve the live App/API object when worker init ran too early."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                return getattr(app, "api", None)
        except Exception:
            pass

        try:
            from airunner.components.server.api.server import get_api

            return get_api()
        except Exception:
            return None

    @staticmethod
    def _main_window_api():
        """Return the API exposed by the active GUI main window."""
        main_window = TTSGeneratorWorker._main_window()
        if main_window is None:
            return None
        return getattr(main_window, "api", None) or getattr(
            getattr(main_window, "app", None),
            "api",
            None,
        )

    @staticmethod
    def _main_window():
        """Return the active GUI main window when one exists."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                return None

            return getattr(app, "main_window", None)
        except Exception:
            return None

    def _daemon_client(self):
        api = self._current_api()
        if api is None or getattr(api, "headless", False):
            return None
        client = getattr(api, "daemon_client", None)
        if client is not None:
            return client

        main_window_getter = getattr(
            self,
            "_main_window",
            TTSGeneratorWorker._main_window,
        )
        main_window = main_window_getter()
        if main_window is None:
            return None

        worker_manager = getattr(main_window, "worker_manager", None)
        daemon_getter = getattr(worker_manager, "_daemon_client", None)
        if callable(daemon_getter):
            client = daemon_getter()
            if client is not None:
                return client

        for candidate in (
            getattr(main_window, "api", None),
            getattr(getattr(main_window, "app", None), "api", None),
        ):
            candidate = TTSGeneratorWorker._normalize_api_candidate(candidate)
            if candidate is None or getattr(candidate, "headless", False):
                continue
            client = getattr(candidate, "daemon_client", None)
            if client is not None:
                return client
        return None

    def _active_tts_model(self) -> Optional[str]:
        """Return the currently selected TTS model name."""
        return AIRUNNER_TTS_MODEL_TYPE or self.chatbot_voice_settings.model_type

    def _report_tts_load_error(self, error: Exception) -> None:
        """Surface one local TTS load failure to the application boundary."""
        api = self._current_api()
        reporter = getattr(api, "application_error", None)
        if callable(reporter):
            reporter(error)
            return
        self.logger.error("TTS load failed: %s", error)

    def _current_tts_status(self) -> ModelStatus:
        """Return the active local TTS runtime status."""
        if self.tts is None:
            return ModelStatus.UNLOADED

        status = getattr(self.tts, "status", None)
        if isinstance(status, ModelStatus):
            return status

        model_status = getattr(self.tts, "model_status", None)
        if isinstance(model_status, dict):
            return model_status.get(ModelType.TTS, ModelStatus.UNLOADED)
        if isinstance(model_status, ModelStatus):
            return model_status
        return ModelStatus.UNLOADED

    def on_llm_text_streamed_signal(self, data):
        if not self.tts_enabled:
            return
        response = data.get("response", None)

        if not response:
            raise ValueError("No LLMResponse object found in data")

        if response.action is LLMActionType.GENERATE_IMAGE:
            return

        # Skip system/status messages (e.g., "model loaded and ready")
        if getattr(response, 'is_system_message', False):
            return

        TTSGeneratorWorker._sync_llm_stream_state(
            self,
            getattr(response, "request_id", None),
            is_first_message=bool(
                getattr(response, "is_first_message", False)
            ),
        )

        cleaned_message = strip_thinking_tags(response.message).replace(
            "</s>", ""
        )
        if cleaned_message:
            self._llm_raw_visible_chunks.append(cleaned_message)

        queued_message = TTSGeneratorWorker._visible_tts_delta(self)
        has_speakable_text = bool(queued_message.strip())
        if not has_speakable_text and not response.is_end_of_message:
            return

        # Initialize local TTS only when daemon-backed execution is inactive.
        active_model = self._active_tts_model()
        failed_local_model = (
            active_model is not None
            and self._failed_model == active_model
        )
        if self._daemon_client() is None and not failed_local_model:
            if not self.tts or self._current_tts_status() not in [
                ModelStatus.LOADED,
                ModelStatus.LOADING,
            ]:
                self._load_tts()
        
        # Unblock TTS if it was interrupted - any new message should resume TTS
        if self.do_interrupt:
            self.logger.debug("Unblocking TTS due to new message")
            self.on_unblock_tts_generator_signal(None)

        if queued_message and response.is_end_of_message:
            if queued_message[-1] not in ".!?":
                queued_message += "."

        self.add_to_queue(
            {
                "message": queued_message,
                "is_end_of_message": response.is_end_of_message,
            }
        )

        if response.is_end_of_message:
            TTSGeneratorWorker._reset_llm_stream_state(self)

    def on_interrupt_process_signal(self, data: dict = None):
        client = self._daemon_client()
        request_id = self._active_request_id
        if client is not None and request_id is not None:
            try:
                client.cancel_runtime(
                    "tts",
                    deployment_mode="sidecar",
                    request_id=request_id,
                    auto_start=False,
                )
            except RuntimeError:
                pass
            self._active_request_id = None
        self.play_queue = []
        self.play_queue_started = False
        self.tokens = []
        self._sentence_buffer = []  # Clear buffered sentences on interrupt
        self.queue = queue.Queue()
        self.do_interrupt = True
        self.paused = True
        TTSGeneratorWorker._reset_llm_stream_state(self)
        if self.tts:
            self.tts.interrupt_process_signal()

    def on_unblock_tts_generator_signal(self, data: Optional[Dict]):
        if self.tts_enabled:
            self.logger.debug("Unblocking TTS generation...")
            self.do_interrupt = False
            self.paused = False
            if self.tts:
                self.tts.unblock_tts_generator_signal()
        if data is not None:
            callback = data.get("callback", None)
            if callback is not None:
                callback()

    def on_enable_tts_signal(self, data: dict = None):
        self.logger.debug("ON ENABLE TTS SIGNAL")
        self._failed_model = None
        self._load_tts()

    def on_disable_tts_signal(self, data: dict = None):
        self._unload_tts()

    def start_worker_thread(self):
        if self.tts_enabled:
            self._load_tts()

    def _reload_tts_model_manager(self, data: dict):
        self.logger.info("Reloading TTS handler...")
        new_model = data.get("model") if data else None
        self.logger.info(
            f"Current model: {self._current_model} | New model: {new_model}"
        )
        if new_model is None or self._current_model == new_model:
            return

        old_tts = self.tts
        self._current_model = new_model
        self._failed_model = None
        self.tts = None

        if old_tts is not None:
            old_tts.unload()

        self._load_tts()

    def on_application_settings_changed_signal(self, data):
        # Handle settings changes that require TTS model updates
        setting_name = data.get("setting_name", "") if data else ""
        column_name = data.get("column_name", "") if data else ""
        value = data.get("val") if data else None
        if value is None and data:
            value = data.get("value")

        if setting_name != "openvoice_settings":
            return

        if self._daemon_client() is not None:
            return

        if column_name != "reference_speaker_path":
            return

        if self.tts and hasattr(self.tts, "reload_speaker_embeddings"):
            self.tts.reload_speaker_embeddings(reference_speaker_path=value)
            return

        if self._active_tts_model() != TTSModel.OPENVOICE.value:
            return

        self._initialize_tts_model_manager()
        if self.tts and hasattr(self.tts, "reload_speaker_embeddings"):
            self.tts.reload_speaker_embeddings(reference_speaker_path=value)
            if self.tts_enabled:
                self._load_tts()

    def _initialize_tts_model_manager(self):
        self.logger.info("Initializing TTS handler...")
        model = self._active_tts_model()
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
        if model_type is TTSModel.OPENVOICE:
            from airunner.components.tts.managers.openvoice_model_manager import (
                OpenVoiceModelManager,
            )

            tts_model_manager_class_ = OpenVoiceModelManager
        else:
            from airunner.components.tts.managers.espeak_model_manager import (
                EspeakModelManager,
            )

            tts_model_manager_class_ = EspeakModelManager
        self.tts = tts_model_manager_class_()
        self.logger.debug(f"Instantiated new TTS model manager: {self.tts}")

    def on_add_to_queue_signal(self, data):
        self.add_to_queue(
            {
                "message": str(data.get("message", "")),
                "is_end_of_message": data.get("is_end_of_message", False)
                is True,
            }
        )

    def add_to_queue(self, message):
        if self.do_interrupt:
            return
        super().add_to_queue(message)

    def get_item_from_queue(self):
        if self.do_interrupt:
            return None
        return super().get_item_from_queue()

    def handle_message(self, data):
        message_type = data.get("_message_type") if data else None
        if message_type == "interrupt":
            self.on_interrupt_process_signal(data.get("data"))
            return
        if message_type == "tts_enable":
            self.on_enable_tts_signal(data.get("data"))
            return
        if message_type == "tts_disable":
            self.on_disable_tts_signal(data.get("data"))
            return

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
        text = combine_stream_chunks(self.tokens)

        # Regular expression to match timestamps in the format HH:MM
        timestamp_pattern = re.compile(r"\b(\d{1,2}):(\d{2})\b")

        # Replace the colon in the matched timestamps with a space
        text = timestamp_pattern.sub(r"\1 \2", text)

        def word_count(s):
            return len(s.split())

        if is_end_of_message:
            # End of message - flush any buffered sentences plus remaining text
            if self._sentence_buffer or text.strip():
                # Combine buffered sentences with any remaining text
                all_text = " ".join(self._sentence_buffer)
                if text.strip():
                    all_text = (all_text + " " + text.strip()).strip()
                if all_text:
                    self._generate(all_text)
                    self.play_queue_started = True
            self._sentence_buffer = []
            self.tokens = []
        else:
            # Split text only at major sentence boundaries for better prosody
            sentence_endings = [".", "?", "!", "\n"]
            for p in sentence_endings:
                if self.do_interrupt:
                    return
                text = text.strip()
                if p in text:
                    split_text = text.split(
                        p, 1
                    )  # Split at the first occurrence of punctuation
                    if len(split_text) > 1:
                        before, after = split_text[0], split_text[1]
                        # Only consider if we have meaningful content (at least 2 words)
                        if word_count(before) >= 2:
                            sentence = (
                                before + p
                            )  # Include the punctuation in the sentence

                            # Add to sentence buffer instead of generating immediately
                            self._sentence_buffer.append(sentence)

                            # Calculate total buffered words
                            total_words = sum(
                                word_count(s)
                                for s in self._sentence_buffer
                            )

                            # Generate if we have enough sentences OR enough words
                            should_generate = (
                                len(self._sentence_buffer)
                                >= self.SENTENCE_BUFFER_SIZE
                                or total_words
                                >= self.MIN_WORDS_FOR_GENERATION
                            )

                            if should_generate:
                                # Combine all buffered sentences and generate
                                combined_text = " ".join(
                                    self._sentence_buffer
                                )
                                self._generate(combined_text)
                                self.play_queue_started = True
                                self._sentence_buffer = []

                            # Set tokens to the remaining text
                            remaining_text = after.strip()
                            if not self.do_interrupt:
                                self.tokens = (
                                    [remaining_text]
                                    if remaining_text
                                    else []
                                )
                            break

        if self.do_interrupt:
            self.on_interrupt_process_signal()

    def _load_tts(self):
        if self._daemon_client() is not None:
            return
        if not self.tts_enabled:
            self.logger.info("TTS is disabled. Skipping load.")
            return

        model = self._active_tts_model()
        if model is not None and self._failed_model == model:
            return

        try:
            if not self.tts:
                self.logger.info("Initializing TTS model manager...")
                self._initialize_tts_model_manager()

            if self.tts:
                self.logger.info("Loading TTS model manager...")
                loaded = self.tts.load()
                if loaded is False:
                    self.logger.info(
                        "TTS model manager did not finish loading."
                    )
                    self.tts = None
                    self._failed_model = model
                    return
                self._failed_model = None
        except (FileNotFoundError, ImportError, OpenVoiceError) as e:
            self.tts = None
            self._failed_model = model
            self._report_tts_load_error(e)
        except Exception as e:
            self.tts = None
            self._failed_model = model
            self._report_tts_load_error(e)

    def load(self):
        self._load_tts()

    def unload(self):
        self._unload_tts()

    def _unload_tts(self):
        if self._daemon_client() is not None:
            self._active_request_id = None
            return
        if self.tts:
            self.tts.unload()

    def _log_tts_input(self, message: str) -> None:
        """Log the exact speakable text passed to TTS."""
        log_info = getattr(self.logger, "info", None)
        if not callable(log_info):
            return
        preview = message if len(message) <= 200 else f"{message[:200]}..."
        log_info("TTS input (%d chars): %r", len(message), preview)

    def _generate(self, message):
        if self.do_interrupt:
            return
        self.logger.debug("Generating TTS...")

        if type(message) == dict:
            message = message.get("message", "")

        # Preprocess message for TTS: replace code/LaTeX with speakable text
        message = FormatterExtended.to_speakable_text(message)
        TTSGeneratorWorker._log_tts_input(self, message)

        model = (
            AIRUNNER_TTS_MODEL_TYPE or self.chatbot_voice_settings.model_type
        )

        if model is None:
            self.logger.error("No TTS model found. Skipping generation.")
            return

        model_type = TTSModel(model)

        self.logger.debug(f"self.tts: {self.tts} | model_type: {model_type}")

        response = None
        client = self._daemon_client()
        if client is not None:
            response = self._generate_via_daemon(message, model)

        tts_req: Optional[Type[TTSRequest]] = None
        if model_type is TTSModel.OPENVOICE:
            tts_req = OpenVoiceTTSRequest(
                message=message, gender=self.chatbot.gender
            )
        elif model_type is TTSModel.ESPEAK:
            tts_req = EspeakTTSRequest(
                message=message,
                gender=self.chatbot.gender,
                rate=self.espeak_settings.rate,
                pitch=self.espeak_settings.pitch,
                volume=self.espeak_settings.volume,
                voice=self.espeak_settings.voice,
                language=self.espeak_settings.language,
            )

        if response is None and self.tts and tts_req:
            if client is not None:
                self.logger.warning(
                    "Falling back to local TTS generation after daemon failure"
                )
            response = self.tts.generate(tts_req)

        if self.do_interrupt:
            return

        if response is not None:
            self.emit_signal(
                SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
                {"message": response},
            )

    def _generate_via_daemon(
        self,
        message: str,
        model_type: Optional[str],
    ):
        client = self._daemon_client()
        if client is None:
            return None
        request_id = str(uuid4())
        self._active_request_id = request_id
        try:
            audio_bytes = client.synthesize_tts(
                message,
                voice=getattr(self.chatbot_voice_settings, "voice", None),
                model=getattr(self.path_settings, "tts_model_path", None),
                model_type=model_type,
                request_id=request_id,
            )
            return self._decode_daemon_audio(audio_bytes)
        except RuntimeError as exc:
            self.logger.error(f"Daemon TTS generation failed: {exc}")
            return None
        finally:
            self._active_request_id = None

    @staticmethod
    def _decode_daemon_audio(audio_bytes: bytes):
        audio, _sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if getattr(audio, "ndim", 1) > 1:
            return audio[:, 0]
        return audio
