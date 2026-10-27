"""Service-owned TTS generator worker."""

import io
import queue
import re
import threading
from typing import Dict, Optional, Type
from uuid import uuid4

import soundfile as sf

from airunner_services.contract_enums import (
    LLMActionType,
    ModelStatus,
    ModelType,
    TTSModel,
)
from airunner_services.settings import AIRUNNER_TTS_MODEL_TYPE
from airunner_services.settings import AIRUNNER_TTS_ON
from airunner_services.utils.text.formatter_extended import FormatterExtended
from airunner_services.llm.thinking_parser import (
    normalize_thinking_content,
    strip_stored_thinking_prefix,
    strip_thinking_tags,
)
from airunner_services.requests.tts_request import EspeakTTSRequest
from airunner_services.requests.tts_request import OpenVoiceTTSRequest
from airunner_services.requests.tts_request import TTSRequest
from airunner_services.runtimes.openvoice_exceptions import OpenVoiceError
from airunner_services.utils.application import peek_registered_api
from airunner_services.utils.application.enum_resolver import signal_code_proxy
from airunner_services.workers.worker import QueueType, Worker

SignalCode = signal_code_proxy(
    {
        "TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL": (
            "TTSGeneratorWorker_add_to_stream_signal"
        ),
        "TTS_ENABLE_SIGNAL": "tts_enable_signal",
    }
)


class TTSGeneratorWorker(Worker):
    """Generate TTS audio from streamed or queued text."""

    tokens = []
    queue_type = QueueType.GET_NEXT_ITEM

    SENTENCE_BUFFER_SIZE = 2
    MIN_WORDS_FOR_GENERATION = 8
    DAEMON_MIN_WORDS_FOR_GENERATION = 4

    def __init__(self, *args, **kwargs):
        self.tts = None
        self.play_queue = []
        self.play_queue_started = False
        self.do_interrupt = False
        self._current_model: Optional[str] = None
        self._failed_model: Optional[str] = None
        self._sentence_buffer = []
        self._active_request_id: Optional[str] = None
        self._reset_llm_stream_state()
        self.signal_handlers = {
            SignalCode.TTS_ENABLE_SIGNAL: self.on_enable_tts_signal,
        }
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
            request_id
            and current_request_id
            and request_id != current_request_id
        ) or (is_first_message and not same_request):
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
            "".join(raw_chunks),
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

    def _current_visible_tts_text(self) -> str:
        """Return the full visible reply currently buffered for speech."""
        if getattr(self, "_llm_thinking_active", False):
            return ""
        return strip_stored_thinking_prefix(
            "".join(getattr(self, "_llm_raw_visible_chunks", [])),
            getattr(self, "_llm_thinking_content", None),
        )

    def _generate_daemon_visible_reply_async(self, message: str) -> None:
        """Generate one daemon-backed GUI reply without the worker queue hop."""
        threading.Thread(
            target=self._generate,
            args=(message,),
            daemon=True,
        ).start()

    def _forward_gui_audio_response(self, response) -> bool:
        """Forward one synthesized audio buffer into the live GUI playback path."""
        api = self._current_api()
        if api is None or False:
            return False
        main_window = getattr(api, "main_window", None) or getattr(
            getattr(api, "app", None),
            "main_window",
            None,
        )
        if main_window is None:
            return False
        worker_manager = getattr(main_window, "worker_manager", None)
        if worker_manager is None:
            return False
        handler = getattr(
            worker_manager,
            "on_tts_generator_worker_add_to_stream_signal",
            None,
        )
        if not callable(handler):
            return False
        handler({"message": response})
        return True

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
            if candidate is None or False:
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
        if (
            root_api is not None
            and getattr(
                candidate,
                "daemon_client",
                None,
            )
            is None
        ):
            return root_api

        app_api = getattr(getattr(candidate, "app", None), "api", None)
        if (
            app_api is not None
            and getattr(
                candidate,
                "daemon_client",
                None,
            )
            is None
        ):
            return app_api
        return candidate

    @staticmethod
    def _resolve_api_instance():
        """Resolve the registered App/API object when worker init ran early."""
        return peek_registered_api()

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
        """Return the registered GUI main window when one exists."""
        api = TTSGeneratorWorker._normalize_api_candidate(
            peek_registered_api()
        )
        if api is None:
            return None
        return getattr(api, "main_window", None)

    def _daemon_client(self):
        api = self._current_api()
        if api is None or False:
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
            if candidate is None or False:
                continue
            client = getattr(candidate, "daemon_client", None)
            if client is not None:
                return client
        return None

    def _active_tts_model(self) -> Optional[str]:
        """Return the currently selected TTS model name."""
        return (
            AIRUNNER_TTS_MODEL_TYPE or self.chatbot_voice_settings.model_type
        )

    def _has_daemon_tts_capability(self) -> bool:
        """Return whether streamed TTS should use the daemon path."""
        current_api_getter = getattr(self, "_current_api", None)
        if callable(current_api_getter):
            return TTSGeneratorWorker._daemon_client(self) is not None

        daemon_client_getter = getattr(self, "_daemon_client", None)
        if callable(daemon_client_getter):
            return daemon_client_getter() is not None
        return False

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
        response = data.get("response", None)
        if data.get("_skip_worker_manager_tts"):
            return
        if response is not None and getattr(
            response, "skip_tts_stream", False
        ):
            return
        if not self.tts_enabled:
            return

        if not response:
            raise ValueError("No LLMResponse object found in data")

        if response.action is LLMActionType.GENERATE_IMAGE:
            return

        if getattr(response, "is_system_message", False):
            return

        TTSGeneratorWorker._sync_llm_stream_state(
            self,
            getattr(response, "request_id", None),
            is_first_message=bool(
                getattr(response, "is_first_message", False)
            ),
        )

        cleaned_message = strip_thinking_tags(response.message).replace(
            "</s>",
            "",
        )
        if cleaned_message:
            self._llm_raw_visible_chunks.append(cleaned_message)

        if TTSGeneratorWorker._has_daemon_tts_capability(self):
            if self.do_interrupt:
                self.logger.debug("Unblocking TTS due to new message")
                self.on_unblock_tts_generator_signal(None)
            if response.is_end_of_message:
                final_message = TTSGeneratorWorker._current_visible_tts_text(
                    self
                ).strip()
                if final_message:
                    if final_message[-1] not in ".!?":
                        final_message += "."
                    self._generate_daemon_visible_reply_async(final_message)
                TTSGeneratorWorker._reset_llm_stream_state(self)
            return

        if not response.is_end_of_message:
            return

        queued_message = (
            getattr(response, "final_visible_message", None)
            or TTSGeneratorWorker._current_visible_tts_text(self).strip()
        )
        if not queued_message:
            TTSGeneratorWorker._reset_llm_stream_state(self)
            return

        active_model = self._active_tts_model()
        failed_local_model = (
            active_model is not None
            and getattr(self, "_failed_model", None) == active_model
        )
        if (
            not TTSGeneratorWorker._has_daemon_tts_capability(self)
            and not failed_local_model
        ):
            if not self.tts or self._current_tts_status() not in [
                ModelStatus.LOADED,
                ModelStatus.LOADING,
            ]:
                self._load_tts()

        if self.do_interrupt:
            self.logger.debug("Unblocking TTS due to new message")
            self.on_unblock_tts_generator_signal(None)

        if queued_message[-1] not in ".!?":
            queued_message += "."

        self.add_to_queue(
            {
                "message": queued_message,
                "is_end_of_message": True,
            }
        )

        TTSGeneratorWorker._reset_llm_stream_state(self)

    def on_interrupt_process_signal(self, data: dict = None):
        client = self._daemon_client()
        request_id = self._active_request_id
        if client is not None and request_id is not None:
            try:
                client.cancel_runtime(
                    "tts",
                    deployment_mode="local_fallback",
                    request_id=request_id,
                    auto_start=False,
                )
            except RuntimeError:
                pass
            self._active_request_id = None
        self.play_queue = []
        self.play_queue_started = False
        self.tokens = []
        self._sentence_buffer = []
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
        if self.tts and self._current_model == model:
            self.logger.debug(
                "TTS model already initialized and matches current model."
            )
            return
        self._current_model = model
        if model_type is TTSModel.OPENVOICE:
            from airunner_services.runtimes.openvoice_model_manager import (
                OpenVoiceModelManager,
            )

            tts_model_manager_class_ = OpenVoiceModelManager
        else:
            from airunner_services.runtimes.espeak_model_manager import (
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

    @staticmethod
    def _is_control_queue_message(message) -> bool:
        """Return whether one queued payload must bypass interrupt drops."""
        if not isinstance(message, dict):
            return False
        message_type = message.get("_message_type")
        return isinstance(message_type, str) and bool(message_type.strip())

    def add_to_queue(self, message):
        if self.do_interrupt and not self._is_control_queue_message(message):
            return
        super().add_to_queue(message)

    def get_item_from_queue(self):
        message = super().get_item_from_queue()
        if message is None:
            return None
        if self.do_interrupt and not self._is_control_queue_message(message):
            return None
        return message

    def handle_message(self, data):
        message_type = data.get("_message_type") if data else None
        if message_type == "interrupt":
            self.on_interrupt_process_signal(data.get("data"))
            return
        if message_type == "unblock_tts_generator":
            self.on_unblock_tts_generator_signal(data.get("data"))
            return
        if message_type == "llm_text_streamed":
            self.on_llm_text_streamed_signal(data.get("data") or {})
            return
        if message_type == "llm_thinking":
            self.on_llm_thinking_signal(data.get("data") or {})
            return
        if message_type == "application_settings_changed":
            self.on_application_settings_changed_signal(data.get("data") or {})
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

        if isinstance(message, str):
            self.tokens.append(message)
        else:
            self.tokens.extend(message)

        text = "".join(self.tokens)
        timestamp_pattern = re.compile(r"\b(\d{1,2}):(\d{2})\b")
        text = timestamp_pattern.sub(r"\1 \2", text)

        def word_count(s):
            return len(s.split())

        word_threshold = (
            TTSGeneratorWorker._sentence_generation_word_threshold(self)
        )

        if is_end_of_message:
            if self._sentence_buffer or text.strip():
                all_text = " ".join(self._sentence_buffer)
                if text.strip():
                    all_text = (all_text + " " + text.strip()).strip()
                if all_text:
                    self._generate(all_text)
                    self.play_queue_started = True
            self._sentence_buffer = []
            self.tokens = []
        else:
            sentence_endings = [".", "?", "!", "\n"]
            for punctuation in sentence_endings:
                if self.do_interrupt:
                    return
                text = text.strip()
                if punctuation in text:
                    split_text = text.split(punctuation, 1)
                    if len(split_text) > 1:
                        before, after = split_text[0], split_text[1]
                        if word_count(before) >= 2:
                            sentence = before + punctuation
                            self._sentence_buffer.append(sentence)

                            total_words = sum(
                                word_count(sentence_text)
                                for sentence_text in self._sentence_buffer
                            )

                            should_generate = (
                                len(self._sentence_buffer)
                                >= self.SENTENCE_BUFFER_SIZE
                                or total_words >= word_threshold
                            )

                            if should_generate:
                                combined_text = " ".join(self._sentence_buffer)
                                self._generate(combined_text)
                                self.play_queue_started = True
                                self._sentence_buffer = []

                            remaining_text = after.strip()
                            if not self.do_interrupt:
                                self.tokens = (
                                    [remaining_text] if remaining_text else []
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
        except (FileNotFoundError, ImportError, OpenVoiceError) as error:
            self.tts = None
            self._failed_model = model
            self._report_tts_load_error(error)
        except Exception as error:
            self.tts = None
            self._failed_model = model
            self._report_tts_load_error(error)

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

    def _sentence_generation_word_threshold(self) -> int:
        """Return the buffered-word threshold before generating speech."""
        default_threshold = getattr(
            self,
            "MIN_WORDS_FOR_GENERATION",
            TTSGeneratorWorker.MIN_WORDS_FOR_GENERATION,
        )
        daemon_client_getter = getattr(self, "_daemon_client", None)
        if (
            callable(daemon_client_getter)
            and daemon_client_getter() is not None
        ):
            return getattr(
                self,
                "DAEMON_MIN_WORDS_FOR_GENERATION",
                TTSGeneratorWorker.DAEMON_MIN_WORDS_FOR_GENERATION,
            )
        return default_threshold

    def _generate(self, message):
        if self.do_interrupt:
            return
        self.logger.debug("Generating TTS...")

        if isinstance(message, dict):
            message = message.get("message", "")

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
        failed_local_model = (
            model is not None and getattr(self, "_failed_model", None) == model
        )
        current_tts_status_getter = getattr(self, "_current_tts_status", None)
        current_tts_status = (
            current_tts_status_getter()
            if callable(current_tts_status_getter)
            else TTSGeneratorWorker._current_tts_status(self)
        )
        if client is None and not failed_local_model:
            needs_local_load = self.tts is None
            if not needs_local_load and hasattr(self.tts, "load"):
                needs_local_load = current_tts_status not in [
                    ModelStatus.LOADED,
                    ModelStatus.LOADING,
                ]
            if needs_local_load:
                self._load_tts()
        if client is not None:
            response = self._generate_via_daemon(message, model)

        tts_req: Optional[Type[TTSRequest]] = None
        if model_type is TTSModel.OPENVOICE:
            tts_req = OpenVoiceTTSRequest(
                message=message,
                gender=self.chatbot.gender,
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

        if response is None and self.tts and tts_req and client is None:
            response = self.tts.generate(tts_req)

        if self.do_interrupt:
            return

        if response is not None:
            if self._forward_gui_audio_response(response):
                return
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
