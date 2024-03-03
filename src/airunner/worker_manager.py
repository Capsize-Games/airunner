import traceback
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal
from airunner.enums import EngineRequestCode, EngineResponseCode, SignalCode
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.workers.audio_capture_worker import AudioCaptureWorker
from airunner.workers.audio_processor_worker import AudioProcessorWorker
from airunner.workers.tts_generator_worker import TTSGeneratorWorker
from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker
from airunner.workers.llm_request_worker import LLMRequestWorker
from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.engine_request_worker import EngineRequestWorker
from airunner.workers.engine_response_worker import EngineResponseWorker
from airunner.workers.sd_generate_worker import SDGenerateWorker
from airunner.workers.sd_request_worker import SDRequestWorker, SDWorker
from airunner.aihandler.logger import Logger
from airunner.utils import clear_memory, create_worker
from airunner.workers.vision_capture_worker import VisionCaptureWorker
from airunner.workers.vision_processor_worker import VisionProcessorWorker


class Message:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name")
        self.message = kwargs.get("message")
        self.conversation = kwargs.get("conversation")


class WorkerManager(QObject, MediatorMixin):
    """
    The engine is responsible for processing requests and offloading
    them to the appropriate AI model controller.
    """
    # Signals
    request_signal_status = pyqtSignal(str)
    image_generated_signal = pyqtSignal(dict)

    def __init__(
        self,
        disable_sd: bool = False,
        disable_llm: bool = False,
        disable_tts: bool = False,
        disable_stt: bool = False,
        disable_vision_capture: bool = False,
        **kwargs
    ):
        MediatorMixin.__init__(self)
        super().__init__()

        self.llm_loaded: bool = False
        self.sd_loaded: bool = False
        self.message = ""
        self.current_message = ""
        self.do_process_queue = None
        self.do_process_queue = None
        self.logger = Logger(prefix=self.__class__.__name__)
        self.is_capturing_image = False
        clear_memory()
        self.register(SignalCode.STT_HEAR_SIGNAL, self.on_hear_signal)
        self.register(SignalCode.ENGINE_CANCEL_SIGNAL, self.on_engine_cancel_signal)
        self.register(SignalCode.ENGINE_STOP_PROCESSING_QUEUE_SIGNAL, self.on_engine_stop_processing_queue_signal)
        self.register(SignalCode.ENGINE_START_PROCESSING_QUEUE_SIGNAL, self.on_engine_start_processing_queue_signal)
        self.register(SignalCode.LLM_CLEAR_HISTORY_SIGNAL, self.on_clear_llm_history_signal)
        self.register(SignalCode.CLEAR_MEMORY_SIGNAL, self.on_clear_memory_signal)
        self.register(SignalCode.LOG_ERROR_SIGNAL, self.on_error_signal)
        self.register(SignalCode.LOG_WARNING_SIGNAL, self.on_warning_signal)
        self.register(SignalCode.LOG_STATUS_SIGNAL, self.on_status_signal)
        self.register(SignalCode.VISION_CAPTION_GENERATED_SIGNAL, self.on_caption_generated_signal)
        self.register(SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, self.on_EngineResponseWorker_response_signal)
        self.register(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, self.on_text_generate_request_signal)
        self.register(SignalCode.SD_IMAGE_GENERATE_REQUEST_SIGNAL, self.on_image_generate_request_signal)
        self.register(SignalCode.LLM_RESPONSE_SIGNAL, self.on_llm_response_signal)
        self.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, self.on_llm_text_streamed_signal)
        self.register(SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL, self.on_AudioCaptureWorker_response_signal)
        self.register(SignalCode.AUDIO_PROCESSOR_WORKER_PROCESSED_SIGNAL, self.on_AudioProcessorWorker_processed_audio)
        self.register(SignalCode.VISION_CAPTURED_SIGNAL, self.on_vision_captured)
        self.register(SignalCode.TTS_REQUEST, self.on_tts_request)
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)

        # if not disable_sd:
        #     self.sd_request_worker = create_worker(SDRequestWorker)
        #     self.sd_generate_worker = create_worker(SDGenerateWorker)

        self.sd_worker = create_worker(SDWorker)

        self.engine_request_worker = create_worker(EngineRequestWorker)
        self.engine_response_worker = create_worker(EngineResponseWorker)

        if not disable_tts:
            self.tts_generator_worker = create_worker(TTSGeneratorWorker)
            self.tts_vocalizer_worker = create_worker(TTSVocalizerWorker)

        if not disable_llm:
            self.llm_request_worker = create_worker(LLMRequestWorker)
            self.llm_generate_worker = create_worker(LLMGenerateWorker)

        if not disable_stt:
            self.stt_audio_capture_worker = create_worker(AudioCaptureWorker)
            self.stt_audio_processor_worker = create_worker(AudioProcessorWorker)

        if not disable_vision_capture:
            self.vision_capture_worker = create_worker(VisionCaptureWorker)
            self.vision_processor_worker = create_worker(VisionProcessorWorker)


        self.toggle_vision_capture()

    def do_response(self, response):
        """
        Handle a response from the application by putting it into
        a response worker queue.
        """
        self.engine_response_worker.add_to_queue(response)

    def on_engine_cancel_signal(self, _ignore):
        self.logger.debug("Canceling")
        self.emit(SignalCode.SD_CANCEL_SIGNAL)
        self.engine_request_worker.cancel()

    def on_engine_stop_processing_queue_signal(self):
        self.do_process_queue = False

    def on_engine_start_processing_queue_signal(self):
        self.do_process_queue = True

    def on_hear_signal(self, message):
        """
        This is a slot function for the hear_signal.
        The hear signal is triggered from the speech_to_text.listen function.
        """
        print("HEARD", message)

    def handle_generate_caption(self, message):
        pass

    def on_caption_generated_signal(self, message):
        print("TODO: caption generated signal", message)

    def handle_text_generated(self, message, code):
        print("TODO: handle text generated no stream")

    def toggle_vision_capture(self):
        do_capture_image = self.settings["ocr_enabled"]
        if do_capture_image != self.is_capturing_image:
            self.is_capturing_image = do_capture_image
            if self.is_capturing_image:
                self.emit(SignalCode.VISION_START_CAPTURE)
            else:
                self.emit(SignalCode.VISION_STOP_CAPTURE)

    def on_application_settings_changed_signal(self, message):
        self.toggle_vision_capture()

    def on_vision_captured(self, message):
        self.emit(SignalCode.VISION_CAPTURE_PROCESS_SIGNAL, message)

    def on_AudioCaptureWorker_response_signal(self, message: np.ndarray):
        self.logger.debug("Heard signal")
        self.stt_audio_processor_worker.add_to_queue(message)

    def on_AudioProcessorWorker_processed_audio(self, message: np.ndarray):
        self.logger.debug("Processed audio")
        self.emit(SignalCode.AUDIO_PROCESSOR_PROCESSED_AUDIO, message)
    
    def on_LLMGenerateWorker_response_signal(self, message:dict):
        self.emit(SignalCode.LLM_RESPONSE_SIGNAL, message)
    
    def on_tts_request(self, data: dict):
        self.tts_generator_worker.add_to_queue(data)
    
    def on_llm_response_signal(self, message):
        self.do_response(message)
    
    def EngineRequestWorker_handle_default(self, message):
        self.logger.error(f"Unknown code: {message['code']}")
    
    def on_error_signal(self, message):
        traceback.print_stack()
        self.logger.error(message)

    def on_warning_signal(self, message):
        self.logger.warning(message)

    def on_status_signal(self, message):
        self.logger.debug(message)
        
    def on_EngineResponseWorker_response_signal(self, response:dict):
        self.logger.debug("EngineResponseWorker_response_signal received")
        code = response["code"]
        if code == EngineResponseCode.IMAGE_GENERATED:
            self.emit(SignalCode.SD_IMAGE_GENERATED_SIGNAL, response["message"])

    def on_clear_memory_signal(self):
        clear_memory()

    def on_llm_text_streamed_signal(self, data):
        try:
            if self.settings["tts_enabled"]:
                self.do_tts_request(data["message"], data["is_end_of_message"])
        except TypeError as e:
            self.logger.error(f"Error in on_llm_text_streamed_signal: {e}")
        self.emit(SignalCode.APPLICATION_ADD_BOT_MESSAGE_TO_CONVERSATION, data)

    def on_sd_image_generated_signal(self, message):
        self.emit(SignalCode.SD_IMAGE_GENERATED_SIGNAL, message)

    def on_text_generate_request_signal(self, message):
        self.emit(
            SignalCode.SD_MOVE_TO_CPU_SIGNAL,
            {
                'callback': lambda _message=message: self.emit(SignalCode.LLM_REQUEST_SIGNAL, _message)
            }
        )

    def on_image_generate_request_signal(self, message):
        self.logger.debug("on_image_generate_request_signal received")
        self.emit(SignalCode.LLM_UNLOAD_SIGNAL, {
            'do_unload_model': self.settings["memory_settings"]["unload_unused_models"],
            'move_unused_model_to_cpu': self.settings["memory_settings"]["move_unused_model_to_cpu"],
            'dtype': self.settings["llm_generator_settings"]["dtype"],
            'callback': lambda _message=message: self.do_image_generate_request(_message)
        })
    
    def do_image_generate_request(self, message):
        self.emit(SignalCode.ENGINE_DO_REQUEST_SIGNAL, {
            'code': EngineRequestCode.GENERATE_IMAGE,
            'message': message
        })

    def request_queue_size(self):
        return self.engine_request_worker.queue.qsize()

    def do_listen(self):
        # self.stt_controller.do_listen()
        pass
    
    def unload_stablediffusion(self):
        """
        Unload the Stable Diffusion model from memory.
        """
        self.emit(SignalCode.SD_UNLOAD_SIGNAL)

    def parse_message(self, message):
        if message:
            if message.startswith("\""):
                message = message[1:]
            if message.endswith("\""):
                message = message[:-1]
        return message
    
    def do_tts_request(self, message: str, is_end_of_message: bool=False):
        if self.settings["tts_enabled"]:
            self.emit(SignalCode.TTS_REQUEST, {
                'message': message.replace("</s>", ""),
                'tts_settings': self.settings["tts_settings"],
                'is_end_of_message': is_end_of_message,
            })
    
    def on_clear_llm_history_signal(self):
        self.emit(SignalCode.LLM_CLEAR_HISTORY)
    
    def stop(self):
        self.logger.debug("Stopping")
        self.engine_request_worker.stop()
        self.engine_response_worker.stop()

    @property
    def settings(self):
        return ServiceLocator.get("get_settings")()

    @settings.setter
    def settings(self, value):
        ServiceLocator.get("set_settings")(value)
