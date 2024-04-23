import traceback
import numpy as np
from PySide6.QtCore import QObject, Signal
from airunner.aihandler.stt.whisper_handler import WhisperHandler
from airunner.aihandler.tts.espeak_tts_handler import EspeakTTSHandler
from airunner.enums import SignalCode, EngineResponseCode
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.workers.audio_capture_worker import AudioCaptureWorker
from airunner.workers.audio_processor_worker import AudioProcessorWorker
from airunner.workers.tts_generator_worker import TTSGeneratorWorker
from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker
from airunner.workers.llm_request_worker import LLMRequestWorker
from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.sd_worker import SDWorker
from airunner.aihandler.logger import Logger
from airunner.utils.create_worker import create_worker
# from airunner.workers.vision_capture_worker import VisionCaptureWorker
# from airunner.workers.vision_processor_worker import VisionProcessorWorker


class Message:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name")
        self.message = kwargs.get("message")
        self.conversation = kwargs.get("conversation")


class WorkerManager(QObject, MediatorMixin, SettingsMixin):
    """
    The engine is responsible for processing requests and offloading
    them to the appropriate AI model controller.
    """
    # Signals
    request_signal_status = Signal(str)
    image_generated_signal = Signal(dict)

    def __init__(
        self,
        disable_sd: bool = False,
        disable_llm: bool = False,
        disable_tts: bool = False,
        disable_stt: bool = False,
        disable_vision_capture: bool = False,
        do_load_llm_on_init: bool = False,
        tts_handler_class=EspeakTTSHandler,
        **kwargs
    ):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__()

        self.llm_loaded: bool = False
        self.sd_loaded: bool = False
        self.message = ""
        self.current_message = ""
        self.do_process_queue = None
        self.do_process_queue = None
        self.logger = Logger(prefix=self.__class__.__name__)
        self.is_capturing_image = False
        self.register(SignalCode.STT_HEAR_SIGNAL, self.on_hear_signal)
        self.register(SignalCode.ENGINE_CANCEL_SIGNAL, self.on_engine_cancel_signal)
        self.register(SignalCode.ENGINE_STOP_PROCESSING_QUEUE_SIGNAL, self.on_engine_stop_processing_queue_signal)
        self.register(SignalCode.ENGINE_START_PROCESSING_QUEUE_SIGNAL, self.on_engine_start_processing_queue_signal)
        self.register(SignalCode.LOG_ERROR_SIGNAL, self.on_error_signal)
        self.register(SignalCode.LOG_WARNING_SIGNAL, self.on_warning_signal)
        self.register(SignalCode.LOG_STATUS_SIGNAL, self.on_status_signal)
        self.register(SignalCode.VISION_CAPTION_GENERATED_SIGNAL, self.on_caption_generated_signal)
        self.register(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, self.on_text_generate_request_signal)
        self.register(SignalCode.LLM_RESPONSE_SIGNAL, self.on_llm_response_signal)
        self.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, self.on_llm_text_streamed_signal)
        self.register(SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL, self.on_AudioCaptureWorker_response_signal)
        self.register(SignalCode.VISION_CAPTURED_SIGNAL, self.on_vision_captured)
        self.register(SignalCode.TTS_REQUEST, self.on_tts_request)
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)

        self.sd_state = None
        if not disable_sd:
            self.sd_worker = create_worker(SDWorker)
            self.sd_state = "loaded"

        if not disable_tts:
            self.tts_generator_worker = create_worker(TTSGeneratorWorker, tts_handler_class=tts_handler_class)
            self.tts_vocalizer_worker = create_worker(TTSVocalizerWorker)

        if not disable_llm:
            self.llm_request_worker = create_worker(LLMRequestWorker)
            self.llm_generate_worker = create_worker(LLMGenerateWorker, do_load_on_init=do_load_llm_on_init)
            self.register(SignalCode.LLM_REQUEST_WORKER_RESPONSE_SIGNAL, self.llm_generate_worker.on_llm_request_worker_response_signal)
            self.register(SignalCode.LLM_UNLOAD_SIGNAL, self.llm_generate_worker.on_unload_llm_signal)

        if not disable_stt:
            self.stt_audio_capture_worker = create_worker(AudioCaptureWorker)
            self.stt_audio_processor_worker = create_worker(AudioProcessorWorker, stt_handler_class=WhisperHandler)

        # if not disable_vision_capture:
        #     self.vision_capture_worker = create_worker(VisionCaptureWorker)
        #     self.vision_processor_worker = create_worker(VisionProcessorWorker)
        #
        # self.toggle_vision_capture()

    def do_response(self, response):
        """
        Handle a response from the application by putting it into
        a response worker queue.
        """
        self.emit_signal(SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, {
            'code': EngineResponseCode.IMAGE_GENERATED,
            'message': response
        })

    def on_engine_cancel_signal(self, _ignore):
        self.logger.debug("Canceling")
        self.emit_signal(SignalCode.SD_CANCEL_SIGNAL)

    def on_engine_stop_processing_queue_signal(self, _message):
        self.do_process_queue = False

    def on_engine_start_processing_queue_signal(self, _message):
        self.do_process_queue = True

    def on_hear_signal(self, message):
        """
        This is a slot function for the hear_signal.
        The hear signal is triggered from the speech_to_text.listen function.
        """
        print("HEARD", message)

    def handle_generate_caption(self, message):
        pass

    def on_caption_generated_signal(self, message: dict):
        print("TODO: caption generated signal", message)

    def handle_text_generated(self, message, code):
        print("TODO: handle text generated no stream")

    def toggle_vision_capture(self):
        do_capture_image = self.settings["ocr_enabled"]
        if do_capture_image != self.is_capturing_image:
            self.is_capturing_image = do_capture_image
            if self.is_capturing_image:
                self.emit_signal(SignalCode.VISION_START_CAPTURE)
            else:
                self.emit_signal(SignalCode.VISION_STOP_CAPTURE)

    def on_application_settings_changed_signal(self, _message: dict):
        self.toggle_vision_capture()

    def on_vision_captured(self, message: dict):
        self.emit_signal(SignalCode.VISION_CAPTURE_PROCESS_SIGNAL, message)

    def on_AudioCaptureWorker_response_signal(self, message: dict):
        item: np.ndarray = message["item"]
        self.logger.debug("Heard signal")
        self.stt_audio_processor_worker.add_to_queue(item)

    def on_tts_request(self, data: dict):
        self.tts_generator_worker.add_to_queue(data)

    def on_llm_response_signal(self, message: dict):
        self.do_response(message)
    
    def EngineRequestWorker_handle_default(self, message: dict):
        self.logger.error(f"Unknown code: {message['code']}")

    def on_error_signal(self, message: dict):
        traceback.print_stack()
        self.logger.error(message)

    def on_warning_signal(self, message: dict):
        self.logger.warning(message)

    def on_status_signal(self, message: dict):
        self.logger.debug(message)

    def on_llm_text_streamed_signal(self, data: dict):
        try:
            if self.settings["tts_enabled"]:
                self.do_tts_request(data["message"], data["is_end_of_message"])
        except TypeError as e:
            self.logger.error(f"Error in on_llm_text_streamed_signal: {e}")
        self.emit_signal(SignalCode.APPLICATION_ADD_BOT_MESSAGE_TO_CONVERSATION, data)

    def on_sd_image_generated_signal(self, message):
        self.emit_signal(SignalCode.SD_IMAGE_GENERATED_SIGNAL, message)

    def on_text_generate_request_signal(self, data: dict):
        move_unused_model_to_cpu = self.settings["memory_settings"]["move_unused_model_to_cpu"]
        unload_unused_models = self.settings["memory_settings"]["unload_unused_models"]
        if self.sd_state == "loaded":
            message = {
                'callback': lambda _message=data: self.emit_signal(
                    SignalCode.LLM_REQUEST_SIGNAL,
                    _message
                )
            }
            if move_unused_model_to_cpu:
                self.emit_signal(SignalCode.SD_MOVE_TO_CPU_SIGNAL, message)
            elif unload_unused_models:
                self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL, message)
        else:
            self.emit_signal(SignalCode.LLM_REQUEST_SIGNAL, data)

    def do_listen(self):
        # self.stt_controller.do_listen()
        pass
    
    def unload_stablediffusion(self):
        """
        Unload the Stable Diffusion model from memory.
        """
        self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

    def parse_message(self, message):
        if message:
            if message.startswith("\""):
                message = message[1:]
            if message.endswith("\""):
                message = message[:-1]
        return message
    
    def do_tts_request(self, message: str, is_end_of_message: bool=False):
        if self.settings["tts_enabled"]:
            self.emit_signal(SignalCode.TTS_REQUEST, {
                'message': message.replace("</s>", "") + ("." if is_end_of_message else ""),
                'tts_settings': self.settings["tts_settings"],
                'is_end_of_message': is_end_of_message,
            })
