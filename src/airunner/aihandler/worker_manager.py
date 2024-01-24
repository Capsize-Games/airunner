import traceback
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal
from airunner.aihandler.enums import EngineRequestCode, EngineResponseCode
from airunner.aihandler.logger import Logger
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
from airunner.aihandler.tts import TTS
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

    def do_response(self, response):
        """
        Handle a response from the application by putting it into
        a response worker queue.
        """
        self.engine_response_worker.add_to_queue(response)

    def on_engine_cancel_signal(self, _ignore):
        self.logger.info("Canceling")
        self.emit("sd_cancel_signal")
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
        self.logger = Logger(prefix="Engine")
        self.clear_memory()

        self.register("hear_signal", self)
        self.register("engine_cancel_signal", self)
        self.register("engine_stop_processing_queue_signal", self)
        self.register("engine_start_processing_queue_signal", self)
        self.register("clear_llm_history_signal", self)
        self.register("clear_memory_signal", self)
        self.register("error_signal", self)
        self.register("warning_signal", self)
        self.register("status_signal", self)
        self.register("caption_generated_signal", self)
        self.register("EngineResponseWorker_response_signal", self)
        self.register("text_generate_request_signal", self)
        self.register("image_generate_request_signal", self)
        self.register("llm_response_signal", self)
        self.register("llm_text_streamed_signal", self)
        self.register("AudioCaptureWorker_response_signal", self)
        self.register("AudioProcessorWorker_processed_audio", self)

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

        self.register("tts_request", self)
    
    def on_AudioCaptureWorker_response_signal(self, message: np.ndarray):
        self.logger.info("Heard signal")
        self.stt_audio_processor_worker.add_to_queue(message)

    def on_AudioProcessorWorker_processed_audio(self, message: np.ndarray):
        self.logger.info("Processed audio")
        self.emit("processed_audio", message)
    
    def on_LLMGenerateWorker_response_signal(self, message:dict):
        self.emit("llm_response_signal", message)
    
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
            self.emit("image_generated_signal", response["message"])

    def on_clear_memory_signal(self):
        self.clear_memory()

    def on_llm_text_streamed_signal(self, data):
        self.do_tts_request(data["message"], data["is_end_of_message"])
        self.emit("add_bot_message_to_conversation", data)

    def on_sd_image_generated_signal(self, message):
        self.emit("image_generated_signal", message)

    def on_text_generate_request_signal(self, message):
        self.move_sd_to_cpu()
        self.emit("llm_request_signal", message)
    
    def on_image_generate_request_signal(self, message):
        self.logger.info("on_image_generate_request_signal received")
        self.emit("unload_llm_signal", dict(
            do_unload_model=self.memory_settings["unload_unused_models"],
            move_unused_model_to_cpu=self.memory_settings["move_unused_model_to_cpu"],
            dtype=self.llm_generator_settings["dtype"],
            callback=lambda _message=message: self.do_image_generate_request(_message)
        ))
    
    def do_image_generate_request(self, message):
        self.clear_memory()
        self.emit("engine_do_request_signal", dict(
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
        self.emit("unload_stablediffusion_signal")

    def parse_message(self, message):
        if message:
            if message.startswith("\""):
                message = message[1:]
            if message.endswith("\""):
                message = message[:-1]
        return message
    
    def do_tts_request(self, message: str, is_end_of_message: bool=False):
        self.emit("tts_request", dict(
            message=message.replace("</s>", ""),
            tts_settings=self.tts_settings,
            is_end_of_message=is_end_of_message,
        ))
    
    def on_clear_llm_history_signal(self):
        self.emit("clear_history")
    
    def stop(self):
        self.logger.info("Stopping")
        self.engine_request_worker.stop()
        self.engine_response_worker.stop()

    def move_sd_to_cpu(self):
        if ServiceLocator.get("is_pipe_on_cpu")() or not ServiceLocator.get("has_pipe")():
            return
        self.emit("move_pipe_to_cpu_signal")
        self.clear_memory()
    
    def clear_memory(self):
        clear_memory()