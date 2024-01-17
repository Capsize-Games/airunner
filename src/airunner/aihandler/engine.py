import threading
import torch
import traceback
import gc
import json

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread

from airunner.aihandler.logger import Logger
from airunner.workers.worker import Worker
from airunner.aihandler.enums import EngineRequestCode, EngineResponseCode
from airunner.aihandler.image_processor import ImageProcessor
from airunner.aihandler.llm import LLMController
from airunner.aihandler.logger import Logger
from airunner.aihandler.runner import SDController
from airunner.aihandler.speech_to_text import SpeechToText
from airunner.aihandler.tts import TTS


class Message:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name")
        self.message = kwargs.get("message")
        self.conversation = kwargs.get("conversation")


class Engine(QObject):
    """
    The engine is responsible for processing requests and offloading
    them to the appropriate AI model controller.
    """
    logger = Logger(prefix="Engine")

    # Signals
    request_signal_status = pyqtSignal(str)
    hear_signal = pyqtSignal(str)
    text_generated_signal = pyqtSignal(dict)
    image_generated_signal = pyqtSignal(dict)

    # Loaded flags
    llm_loaded: bool = False
    sd_loaded: bool = False

    # Model controllers
    llm_controller = None
    sd_controller = None
    tts_controller = None
    stt_controller = None
    ocr_controller = None

    # Message properties for EngineResponseCode.TEXT_STREAMED
    message = ""
    first_message = True
    current_message = ""

    #######################
    # START OFFLINE CLINET
    def do_request(self, code:EngineRequestCode, message:dict):
        """
        Handle a request from the application by putting it into
        a request worker queue.
        """
        if message == "cancel":
            self.logger.info("cancel message recieved")
            self.cancel()
        else:
            self.request_worker.add_to_queue(dict(
                code=code,
                message=message
            ))

    @pyqtSlot(dict)  
    def do_response(self, response):
        """
        Handle a response from the application by putting it into
        a response worker queue.
        """
        self.response_worker.add_to_queue(dict(
            code=response["code"],
            message=response["message"]
        ))

    def cancel(self):
        self.logger.info("Canceling")
        self.sd_controller.cancel()
        self.request_worker.cancel()

    # END OFFLINE CLIENT
    #######################

    pyqtSlot(str)
    def hear(self, message):
        """
        This is a slot function for the hear_signal.
        The hear signal is triggered from the speech_to_text.listen function.
        """
        self.app.respond_to_voice(heard=message)

    pyqtSlot(dict)
    def request_worker_response_signal_slot(self, message):
        """
        Handle a response from the request worker.
        """
        self.logger.debug(f"message['code']: {message['code']}, type: {type(message['code'])}")
        {
            EngineRequestCode.GENERATE_TEXT: self.handle_generate_text,
            EngineRequestCode.GENERATE_IMAGE: self.handle_generate_image,
            EngineRequestCode.GENERATE_CAPTION: self.handle_generate_caption,
        }.get(message["code"], self.handle_default)(message)
    
    pyqtSlot(dict)
    def response_worker_response_signal_slot(self, message):
        code = message["code"]
        if code == EngineResponseCode.ERROR:
            traceback.print_stack()
            self.logger.error(message)
        elif code == EngineResponseCode.WARNING:
            self.logger.warning(message)
        elif code == EngineResponseCode.STATUS:
            self.logger.info(message)
        if code == EngineResponseCode.TEXT_GENERATED:
            message = self.parse_message(message)
            self.app.message_handler_signal.emit({
                "code": EngineResponseCode.ADD_TO_CONVERSATION,
                "message": dict(
                    name=self.app.settings["llm_generator_settings"]["botname"],
                    text=message,
                    is_bot=True,
                )
            })

        """
        Handle a response from the response worker.
        """
        {
            EngineResponseCode.TEXT_GENERATED: self.handle_text_generated,
            EngineResponseCode.TEXT_STREAMED: self.handle_text_streamed,
            EngineResponseCode.IMAGE_GENERATED: self.handle_image_generated,
            EngineResponseCode.CAPTION_GENERATED: self.handle_caption_generated,
            EngineResponseCode.CLEAR_MEMORY: self.clear_memory
        }.get(message["code"], self.handle_default_response)(message["message"], message["code"])

    def handle_generate_text(self, message):
        self.move_sd_to_cpu()
        self.llm_controller.do_request(message["message"])

    def handle_generate_image(self, message):
        self.unload_llm(
            message, 
            self.app.settings["memory_settings"]["unload_unused_models"], 
            self.app.settings["memory_settings"]["move_unused_model_to_cpu"]
        )
        self.sd_controller.do_request(message["message"])

    def handle_generate_caption(self, message):
        pass

    def handle_text_generated(self, message, code):
        print("TODO: handle text generated no stream")

    def handle_text_streamed(self, message, code):
        self.message += message
        self.current_message += message
        self.message = self.message.replace("</s>", "")
        self.current_message = self.current_message.replace("</s>", "")
        # check if sentence enders are in self.current_message
        is_end_of_message = "</s>" in message
        self.tts_controller.add_text(message.replace("</s>", ""), is_end_of_message=is_end_of_message)
        self.text_generated_signal.emit(dict(
            name=self.app.settings["llm_generator_settings"]["botname"],
            text=message.replace("</s>", ""),
            is_bot=True,
            first_message=self.first_message,
            last_message=is_end_of_message
        ))
        self.first_message = False
        if is_end_of_message:
            self.first_message = True
            self.message = ""
            self.current_message = ""
        
        # self.stt_controller.do_listen()

    def handle_image_generated(self, message, code):
        self.image_generated_signal.emit(message)

    def handle_caption_generated(self, message, code):
        self.send_message(message, code)
    
    def __init__(self, **kwargs):
        super().__init__()
        
        self.app = kwargs.get("app", None)
        self.message_handler = kwargs.get("message_handler", None)
        self.clear_memory()

        # Initialize Controllers
        self.llm_controller = LLMController(engine=self)
        self.sd_controller = SDController(engine=self)
        #self.stt_controller = SpeechToText(engine=self, hear_signal=self.hear_signal, duration=10.0, fs=16000)
        #self.hear_signal.connect(self.hear)
        # self.listen_thread = threading.Thread(target=self.stt_controller.listen)
        # self.listen_thread.start()

        self.tts_controller = TTS(engine=self)
        #self.tts_thread = threading.Thread(target=self.tts_controller.run)
        #self.tts_thread.start()

        # self.ocr_controller = ImageProcessor(engine=self)

        self.llm_controller.response_signal.connect(self.do_response)
        self.sd_controller.response_signal.connect(self.do_response)

        # Request worker and thread
        self.request_worker = Worker(prefix="RequestWorker")
        self.request_worker_thread = QThread()
        self.request_worker.moveToThread(self.request_worker_thread)
        self.request_worker.response_signal.connect(self.request_worker_response_signal_slot)
        self.request_worker.finished.connect(self.request_worker_thread.quit)
        self.request_worker_thread.started.connect(self.request_worker.start)
        self.request_worker_thread.start()

        # # Response worker and thread
        self.response_worker = Worker(prefix="ResponseWorker")
        self.response_worker_thread = QThread()
        self.response_worker.moveToThread(self.response_worker_thread)
        self.response_worker.response_signal.connect(self.response_worker_response_signal_slot)
        self.response_worker.finished.connect(self.response_worker_thread.quit)
        self.response_worker_thread.started.connect(self.response_worker.start)
        self.response_worker_thread.start()

    def handle_default(self, message):
        self.logger.error(f"Unknown code: {message['code']}")
    
    def handle_default_response(self, message, code):
        self.app.send_message(code, message)

    def request_queue_size(self):
        return self.request_worker.queue.qsize()

    def send_message(self, message, code=None):
        """
        Send a message to the Stable Diffusion model.
        """
        if code == EngineResponseCode.IMAGE_GENERATED:
            self.app.message_handler_signal.emit(dict(
                code=code,
                message=message
            ))
    
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

    def cancel(self):
        """
        Cancel Stable Diffusion request.
        """
        self.sd_controller.cancel()
    
    def unload_stablediffusion(self):
        """
        Unload the Stable Diffusion model from memory.
        """
        self.sd_controller.unload()

    def parse_message(self, message):
        if message:
            if message.startswith("\""):
                message = message[1:]
            if message.endswith("\""):
                message = message[:-1]
        return message
    
    def handle_tts(self, message: str):
        if self.app.settings["tts_settings"]["enable_tts"]:
            botname = self.app.settings["llm_generator_settings"]["botname"]
            message = message.strip()
            # self.app.engine.message = dict(
            #     tts_request=True,
            #     request_data=dict(
            #         text=sentence,
            #         message_object=Message(
            #             name=botname,
            #             message=sentence,
            #         ),
            #         is_bot=True,
            #         #signal=self.add_message_signal,
            #         gender=self.app.settings["tts_settings"]["gender"],
            #         first_message=True,
            #         last_message=True,
            #         tts_settings=self.app.settings["tts_settings"]
            #     )
            # )
            self.tts_controller.add_text(message)
    
    def clear_memory(self, *args, **kwargs):
        """
        Clear the GPU ram.
        """
        self.logger.info("Clearing memory")
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        gc.collect()
    
    def clear_llm_history(self):
        if self.llm:
            self.llm_controller.clear_history()
    
    def stop(self):
        self.logger.info("Stopping")
        self.request_worker.stop()
        self.response_worker.stop()
        #self.stt_controller.stop()
    
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
            dtype = self.app.settings["llm_generator_settings"]["dtype"]
            if dtype in ["2bit", "4bit", "8bit"]:
                do_unload_model = True
                do_move_to_cpu = False

        if do_move_to_cpu:
            self.logger.info("Moving LLM to CPU")
            self.llm_controller.move_to_cpu()
            self.clear_memory()
        elif do_unload_model:
            self.do_unload_llm()
    
    def do_unload_llm(self):
        self.logger.info("Unloading LLM")
        self.llm_controller.do_unload_llm()
        self.clear_memory()

    def move_sd_to_cpu(self):
        if self.sd_controller.is_pipe_on_cpu or not self.sd_controller.has_pipe:
            return
        self.sd_controller.move_pipe_to_cpu()
        self.clear_memory()