import traceback
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal
from airunner.aihandler.enums import EngineRequestCode, EngineResponseCode, SignalCode
from airunner.mediator_mixin import MediatorMixin
from airunner.workers.audio_capture_worker import AudioCaptureWorker
from airunner.workers.audio_processor_worker import AudioProcessorWorker
from airunner.workers.tts_generator_worker import TTSGeneratorWorker
from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker
from airunner.workers.llm_request_worker import LLMRequestWorker
from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.engine_request_worker import EngineRequestWorker
from airunner.workers.engine_response_worker import EngineResponseWorker
from airunner.workers.sd_generate_worker import SDGenerateWorker
from airunner.workers.sd_request_worker import SDRequestWorker
from airunner.aihandler.logger import Logger
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.service_locator import ServiceLocator
from airunner.utils import clear_memory
from airunner.workers.vision_capture_worker import VisionCaptureWorker
from airunner.workers.vision_processor_worker import VisionProcessorWorker


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
    request_signal_status = pyqtSignal(str)
    image_generated_signal = pyqtSignal(dict)

    # Loaded flags
    llm_loaded: bool = False
    sd_loaded: bool = False

    message = ""
    current_message = ""
    processed_vision_history = []

    def do_response(self, response):
        """
        Handle a response from the application by putting it into
        a response worker queue.
        """
        self.engine_response_worker.add_to_queue(response)

    def on_engine_cancel_signal(self, _ignore):
        self.logger.info("Canceling")
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
    
    def __init__(self, **kwargs):
        super().__init__()
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.logger = Logger(prefix=self.__class__.__name__)
        self.is_capturing_image = False
        self.clear_memory()
        self.register(SignalCode.HEAR_SIGNAL, self.on_hear_signal)
        self.register(SignalCode.ENGINE_CANCEL_SIGNAL, self.on_engine_cancel_signal)
        self.register(SignalCode.ENGINE_STOP_PROCESSING_QUEUE_SIGNAL, self.on_engine_stop_processing_queue_signal)
        self.register(SignalCode.ENGINE_START_PROCESSING_QUEUE_SIGNAL, self)
        self.register(SignalCode.CLEAR_LLM_HISTORY_SIGNAL, self.on_clear_llm_history_signal)
        self.register(SignalCode.CLEAR_MEMORY_SIGNAL, self.on_clear_memory_signal)
        self.register(SignalCode.ERROR_SIGNAL, self.on_error_signal)
        self.register(SignalCode.WARNING_SIGNAL, self.on_warning_signal)
        self.register(SignalCode.STATUS_SIGNAL, self.on_status_signal)
        self.register(SignalCode.CAPTION_GENERATED_SIGNAL, self.on_caption_generated_signal)
        self.register(SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, self.on_EngineResponseWorker_response_signal)
        self.register(SignalCode.TEXT_GENERATE_REQUEST_SIGNAL, self.on_text_generate_request_signal)
        self.register(SignalCode.IMAGE_GENERATE_REQUEST_SIGNAL, self.on_image_generate_request_signal)
        self.register(SignalCode.LLM_RESPONSE_SIGNAL, self.on_llm_response_signal)
        self.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, self.on_llm_text_streamed_signal)
        self.register(SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL, self.on_AudioCaptureWorker_response_signal)
        self.register(SignalCode.AUDIO_PROCESSOR_WORKER_PROCESSED_SIGNAL, self.on_AudioProcessorWorker_processed_audio)
        self.register(SignalCode.VISION_CAPTURED_SIGNAL, self.on_vision_captured)
        self.register(SignalCode.VISION_PROCESSED_SIGNAL, self.on_vision_processed)

        self.sd_request_worker = self.create_worker(SDRequestWorker)
        self.sd_generate_worker = self.create_worker(SDGenerateWorker)
        
        self.engine_request_worker = self.create_worker(EngineRequestWorker)
        self.engine_response_worker = self.create_worker(EngineResponseWorker)

        self.tts_generator_worker = self.create_worker(TTSGeneratorWorker)
        self.tts_vocalizer_worker = self.create_worker(TTSVocalizerWorker)

        self.llm_request_worker = self.create_worker(LLMRequestWorker)
        self.llm_generate_worker = self.create_worker(LLMGenerateWorker)

        self.stt_audio_capture_worker = self.create_worker(AudioCaptureWorker)
        self.stt_audio_processor_worker = self.create_worker(AudioProcessorWorker)

        self.vision_capture_worker = self.create_worker(VisionCaptureWorker)
        self.vision_processor_worker = self.create_worker(VisionProcessorWorker)

        self.register(SignalCode.TTS_REQUEST, self.on_tts_request)
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)

        self.toggle_vision_capture()

    def toggle_vision_capture(self):
        do_capture_image = self.settings["ocr_enabled"]
        if do_capture_image != self.is_capturing_image:
            self.is_capturing_image = do_capture_image
            if self.is_capturing_image:
                self.emit(SignalCode.START_VISION_CAPTURE)
            else:
                self.emit(SignalCode.STOP_VISION_CAPTURE)

    def on_application_settings_changed_signal(self, message):
        self.toggle_vision_capture()

    def on_vision_captured(self, message):
        self.emit(SignalCode.VISION_CAPTURE_PROCESS_SIGNAL, message)

    def on_vision_processed(self, message):
        self.processed_vision_history.append(message)
        print(self.processed_vision_history)
        self.emit(SignalCode.VISION_CAPTURE_UNPAUSE_SIGNAL)
    
    def on_AudioCaptureWorker_response_signal(self, message: np.ndarray):
        self.logger.info("Heard signal")
        self.stt_audio_processor_worker.add_to_queue(message)

    def on_AudioProcessorWorker_processed_audio(self, message: np.ndarray):
        self.logger.info("Processed audio")
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
        self.logger.info(message)
        
    def on_EngineResponseWorker_response_signal(self, response:dict):
        self.logger.info("EngineResponseWorker_response_signal received")
        code = response["code"]
        if code == EngineResponseCode.IMAGE_GENERATED:
            self.emit(SignalCode.IMAGE_GENERATED_SIGNAL, response["message"])

    def on_clear_memory_signal(self):
        self.clear_memory()

    def on_llm_text_streamed_signal(self, data):
        self.do_tts_request(data["message"], data["is_end_of_message"])
        self.emit(SignalCode.ADD_BOT_MESSAGE_TO_CONVERSATION, data)

    def on_sd_image_generated_signal(self, message):
        self.emit(SignalCode.IMAGE_GENERATED_SIGNAL, message)

    def on_text_generate_request_signal(self, message):
        self.move_sd_to_cpu()
        self.emit(SignalCode.LLM_REQUEST_SIGNAL, message)
    
    def on_image_generate_request_signal(self, message):
        self.logger.info("on_image_generate_request_signal received")
        self.emit(SignalCode.UNLOAD_LLM_SIGNAL, dict(
            do_unload_model=self.memory_settings["unload_unused_models"],
            move_unused_model_to_cpu=self.memory_settings["move_unused_model_to_cpu"],
            dtype=self.llm_generator_settings["dtype"],
            callback=lambda _message=message: self.do_image_generate_request(_message)
        ))
    
    def do_image_generate_request(self, message):
        self.clear_memory()
        self.emit(SignalCode.ENGINE_DO_REQUEST_SIGNAL, dict(
            code=EngineRequestCode.GENERATE_IMAGE, 
            message=message
        ))

    def request_queue_size(self):
        return self.engine_request_worker.queue.qsize()

    def do_listen(self):
        # self.stt_controller.do_listen()
        pass
    
    def unload_stablediffusion(self):
        """
        Unload the Stable Diffusion model from memory.
        """
        self.emit(SignalCode.UNLOAD_SD_SIGNAL)

    def parse_message(self, message):
        if message:
            if message.startswith("\""):
                message = message[1:]
            if message.endswith("\""):
                message = message[:-1]
        return message
    
    def do_tts_request(self, message: str, is_end_of_message: bool=False):
        self.emit(SignalCode.TTS_REQUEST, dict(
            message=message.replace("</s>", ""),
            tts_settings=self.tts_settings,
            is_end_of_message=is_end_of_message,
        ))
    
    def on_clear_llm_history_signal(self):
        self.emit(SignalCode.CLEAR_HISTORY)
    
    def stop(self):
        self.logger.info("Stopping")
        self.engine_request_worker.stop()
        self.engine_response_worker.stop()

    def move_sd_to_cpu(self):
        if ServiceLocator.get("is_pipe_on_cpu")() or not ServiceLocator.get("has_pipe")():
            return
        self.emit(SignalCode.MOVE_TO_CPU_SIGNAL)
        self.clear_memory()
    
    def clear_memory(self):
        clear_memory()