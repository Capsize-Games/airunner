import torch
import traceback
import gc

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from airunner.aihandler.enums import EngineRequestCode, EngineResponseCode
from airunner.aihandler.logger import Logger
from airunner.mediator_mixin import MediatorMixin
from airunner.workers.tts_generator_worker import TTSGeneratorWorker
from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker
from airunner.workers.worker import Worker
from airunner.aihandler.llm import LLMController
from airunner.aihandler.logger import Logger
from airunner.aihandler.runner import SDGenerateWorker, SDRequestWorker
from airunner.aihandler.tts import TTS
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.service_locator import ServiceLocator


class EngineRequestWorker(Worker):
    def __init__(self, prefix="EngineRequestWorker"):
        super().__init__(prefix=prefix)
        self.register("engine_do_request_signal", self)
    
    def on_engine_do_request_signal(self, request):
        self.logger.info("Adding to queue")
        self.add_to_queue(request)
    
    def handle_message(self, request):
        if request["code"] == EngineRequestCode.GENERATE_IMAGE:
            self.emit("sd_request_signal", request)
        else:
            self.logger.error(f"Unknown code: {request['code']}")


class EngineResponseWorker(Worker):
    def __init__(self, prefix="EngineResponseWorker"):
        super().__init__(prefix=prefix)
        self.register("engine_do_response_signal", self)
    
    def on_engine_do_response_signal(self, request):
        self.logger.info("Adding to queue")
        self.add_to_queue(request)


class Message:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name")
        self.message = kwargs.get("message")
        self.conversation = kwargs.get("conversation")


class Engine(QObject, MediatorMixin, SettingsMixin):
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

    # Model controllers
    llm_controller = None
    stt_controller = None
    ocr_controller = None

    message = ""
    current_message = ""

    def do_response(self, response):
        """
        Handle a response from the application by putting it into
        a response worker queue.
        """
        self.response_worker.add_to_queue(response)

    @pyqtSlot(object)
    def on_engine_cancel_signal(self, _ignore):
        self.logger.info("Canceling")
        self.emit("sd_cancel_signal")
        self.request_worker.cancel()

    @pyqtSlot(object)
    def on_engine_stop_processing_queue_signal(self):
        self.do_process_queue = False
    
    @pyqtSlot(object)
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

    @pyqtSlot(object)
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

        # Initialize Controllers
        self.llm_controller = LLMController(engine=self)
        #self.stt_controller = STTController(engine=self)
        # self.ocr_controller = ImageProcessor(engine=self)
        self.tts_controller = TTS(engine=self)

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
        self.register("llm_controller_response_signal", self)
        self.register("llm_text_streamed_signal", self)

        self.sd_request_worker = self.create_worker(SDRequestWorker)
        self.sd_generate_worker = self.create_worker(SDGenerateWorker)
        
        self.request_worker = self.create_worker(EngineRequestWorker)
        self.response_worker = self.create_worker(EngineResponseWorker)

        self.generator_worker = self.create_worker(TTSGeneratorWorker)
        self.vocalizer_worker = self.create_worker(TTSVocalizerWorker)
        self.register("tts_request", self)
    
    @pyqtSlot(dict)
    def on_tts_request(self, data: dict):
        self.generator_worker.add_to_queue(data)
    
    def on_llm_controller_response_signal(self, message):
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

    @pyqtSlot()
    def on_clear_memory_signal(self):
        self.clear_memory()

    @pyqtSlot(object)
    def on_llm_text_streamed_signal(self, data):
        self.do_tts_request(data["message"], data["is_end_of_message"])
        self.emit("add_bot_message_to_conversation", data)

    @pyqtSlot(object)
    def on_sd_image_generated_signal(self, message):
        self.emit("image_generated_signal", message)

    @pyqtSlot(object)
    def on_text_generate_request_signal(self, message):
        self.move_sd_to_cpu()
        self.llm_controller.do_request(message)
    
    @pyqtSlot(object)
    def on_image_generate_request_signal(self, message):
        self.logger.info("on_image_generate_request_signal received")
        # self.unload_llm(
        #     message, 
        #     self.memory_settings["unload_unused_models"], 
        #     self.memory_settings["move_unused_model_to_cpu"]
        # )
        self.emit("engine_do_request_signal", dict(
            code=EngineRequestCode.GENERATE_IMAGE,
            message=message
        ))

    def request_queue_size(self):
        return self.request_worker.queue.qsize()

    # def generator_sample(self, data: dict):
    #     """
    #     This function will determine if the request
    #     :param data:
    #     :return:
    #     """
    #     self.logger.info("generator_sample called")
    #     self.llm_generator_sample(data)
    #     self.tts_generator_sample(data)
    #     self.sd_generator_sample(data)
    
    # def llm_generator_sample(self, data: dict):
    #     if "llm_request" not in data or not self.llm:
    #         return
    #     if not self.llm_loaded:
    #         self.logger.info("Preparing LLM")
    #         # if self.tts:
    #         #     self.tts_controller.move_model(to_cpu=False)
    #         self.llm_loaded = True
    #         do_unload_model = data["request_data"].get("unload_unused_model", False)
    #         do_move_to_cpu = not do_unload_model and data["request_data"].get("move_unused_model_to_cpu", False)
    #         if do_move_to_cpu:
    #             self.move_sd_to_cpu()
    #         elif do_unload_model:
    #             self.sd_controller.unload()
    #     self.logger.info("Engine calling llm.do_generate")
    #     self.llm_controller.do_generate(data)
    
    # def tts_generator_sample(self, data: dict):
    #     if "tts_request" not in data or not self.tts:
    #         return
    #     self.logger.info("Preparing TTS model...")
    #     # self.tts_controller.move_model(to_cpu=False)
    #     signal = data["request_data"].get("signal", None)
    #     message_object = data["request_data"].get("message_object", None)
    #     is_bot = data["request_data"].get("is_bot", False)
    #     first_message = data["request_data"].get("first_message", None)
    #     last_message = data["request_data"].get("last_message", None)
    #     if data["request_data"]["tts_settings"]["enable_tts"]:
    #         text = data["request_data"]["text"]
    #         # check if ends with a proper sentence ender, if not, add a period
    #         if not text.endswith((".", "?", "!", "...", "-", "—", )):
    #             text += "."
    #         generator = self.tts_controller.add_text(text, "a", data["request_data"]["tts_settings"])
    #         for success in generator:
    #             if signal and success:
    #                 signal.emit(message_object, is_bot, first_message, last_message)

    # def sd_generator_sample(self, data:dict):
    #     if "options" not in data or "sd_request" not in data["options"] or not self.sd:
    #         return
    #     if not self.sd_loaded:
    #         self.logger.info("Preparing Stable Diffusion")
    #         self.sd_loaded = True
    #         self.do_unload_llm()
    #     self.logger.info("Engine calling sd.generator_sample")
    #     self.sd_controller.generator_sample(data)

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
    
    def clear_memory(self, *args, **kwargs):
        """
        Clear the GPU ram.
        """
        self.logger.info("Clearing memory")
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        gc.collect()
    
    def on_clear_llm_history_signal(self):
        if self.llm:
            self.llm_controller.clear_history()
    
    def stop(self):
        self.logger.info("Stopping")
        self.request_worker.stop()
        self.response_worker.stop()
    
    def unload_llm(self, request_data: dict, do_unload_model: bool, move_unused_model_to_cpu: bool):
        """
        This function will either 
        
        1. Leave the LLM on the GPU
        2. Move it to the CPU
        3. Unload it from memory

        The choice is dependent on the current dtype and other settings.
        """
        do_move_to_cpu = not do_unload_model and move_unused_model_to_cpu
        
        if request_data:
            # Firist check the dtype
            dtype = self.llm_generator_settings["dtype"]
            if dtype in ["2bit", "4bit", "8bit"]:
                do_unload_model = True
                do_move_to_cpu = False

        if do_move_to_cpu:
            self.logger.info("Moving LLM to CPU")
            self.llm_controller.move_to_cpu()
            self.clear_memory()
        # elif do_unload_model:
        #     self.do_unload_llm()
    
    def do_unload_llm(self):
        self.logger.info("Unloading LLM")
        self.llm_controller.do_unload_llm()
        #self.clear_memory()

    def move_sd_to_cpu(self):
        if ServiceLocator.get("is_pipe_on_cpu")() or not ServiceLocator.get("has_pipe")():
            return
        self.emit("move_pipe_to_cpu_signal")
        self.clear_memory()