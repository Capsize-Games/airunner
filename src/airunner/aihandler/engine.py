import torch
import gc
import threading

from airunner.aihandler.llm import LLM
from airunner.aihandler.logger import Logger as logger
from airunner.aihandler.runner import SDRunner
from airunner.aihandler.tts import TTS
from airunner.aihandler.speech_to_text import SpeechToText
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class Engine(QObject):
    """
    The engine is responsible for processing requests and offloading
    them to the appropriate AI model controller.
    """
    model_type = None
    hear_signal = pyqtSignal(str)
    
    @property
    def hf_api_key_write_key(self):
        return self.sd.hf_api_key_write_key

    def __init__(self, **kwargs):
        super().__init__()
        self.app = kwargs.get("app", None)
        self.message_var = kwargs.get("message_var", None)
        self.message_handler = kwargs.get("message_handler", None)
        self.clear_memory()
        self.llm = LLM(app=self.app, engine=self)
        self.speech_to_text = SpeechToText(
            hear_signal=self.hear_signal,
            engine=self,
            duration=10.0,
            fs=16000
        )
        self.sd = SDRunner(
            app=self.app,
            message_var=self.message_var,
            message_handler=self.message_handler,
            engine=self
        )
        self.hear_signal.connect(self.hear)
        self.tts = TTS(engine=self, use_bark=self.app.tts_settings["use_bark"])
        self.tts_thread = threading.Thread(target=self.tts.run)
        self.tts_thread.start()
        self.listen_thread = threading.Thread(target=self.speech_to_text.listen)
        self.listen_thread.start()
    
    pyqtSlot(str)
    def hear(self, message):
        """
        This is a slot function for the hear_signal.
        The hear signal is triggered from the speech_to_text.listen function.
        """
        print("HEARD: ", message)
        self.app.respond_to_voice(heard=message)

    def move_pipe_to_cpu(self):
        logger.info("Moving pipe to CPU")
        self.sd.move_pipe_to_cpu()
        self.clear_memory()

    def generator_sample(self, data: dict):
        """
        This function will determine if the request
        :param data:
        :return:
        """
        logger.info("generator_sample called")
        is_llm = self.is_llm_request(data)
        is_tts = self.is_tts_request(data)
        self.request_data = data.get("request_data", {})
        tts_settings = self.request_data.get("tts_settings", None)
        if is_llm and self.model_type != "llm":
            logger.info("Switching to LLM model")
            #self.tts.move_model(to_cpu=True)
            self.clear_memory()
            self.model_type = "llm"
            do_unload_model = data["request_data"].get("unload_unused_model", False)
            do_move_to_cpu = not do_unload_model and data["request_data"].get("move_unused_model_to_cpu", False)
            if do_move_to_cpu:
                self.move_pipe_to_cpu()
            elif do_unload_model:
                self.sd.unload_model()
                self.sd.unload_tokenizer()
                self.clear_memory()
            # self.llm.move_to_device()
        elif is_tts:
            logger.info("Engine calling tts")
            #self.tts.move_model(to_cpu=False)
            signal = data["request_data"].get("signal", None)
            message_object = data["request_data"].get("message_object", None)
            is_bot = data["request_data"].get("is_bot", False)
            first_message = data["request_data"].get("first_message", None)
            last_message = data["request_data"].get("last_message", None)
            if self.request_data["tts_settings"]["enable_tts"]:
                generator = self.tts.add_sentence(data["request_data"]["text"], "a", self.request_data["tts_settings"])
                for success in generator:
                    if signal and success:
                        signal.emit(message_object, is_bot, first_message, last_message)
        elif not is_llm and not is_tts and self.model_type != "art":
            logger.info("Switching to art model")
            do_unload_model = data["options"].get("unload_unused_model", False)
            move_unused_model_to_cpu = data["options"].get("move_unused_model_to_cpu", False)
            self.model_type = "art"
            self.unload_llm(do_unload_model, move_unused_model_to_cpu)

        if is_llm:
            logger.info("Engine calling llm.do_generate")
            self.llm.do_generate(data)
        elif not is_tts:
            logger.info("Engine calling sd.generator_sample")
            self.sd.generator_sample(data)
    
    request_data = None

    def do_listen(self):
        self.speech_to_text.do_listen()

    def is_llm_request(self, data):
        return "llm_request" in data

    def is_tts_request(self, data):
        return "tts_request" in data

    def unload_llm(self, do_unload_model, move_unused_model_to_cpu):
        """
        This function will either leave the LLM
        on the GPU, move it to the CPU or unload it.
        The choice is dependent on the current dtype
        and other settings such as use_gpu
        and whether or not the user has enough
        VRAM to keep the LLM loaded while
        using other models.
        """
        do_move_to_cpu = not do_unload_model and move_unused_model_to_cpu
        if self.request_data:
            dtype = self.app.llm_generator_settings["dtype"]
            if dtype in ["2bit", "4bit", "8bit"]:
                do_unload_model = True
                do_move_to_cpu = False

        if do_move_to_cpu:
            logger.info("Moving LLM to CPU")
            self.llm.move_to_cpu()

            self.clear_memory()
        elif do_unload_model:
            logger.info("Unloading LLM")
            self.llm.unload_model()
            self.llm.unload_tokenizer()
            self.clear_memory()

    def cancel(self):
        self.sd.cancel()
    
    def unload_stablediffusion(self):
        self.sd.unload()

    def send_message(self, message, code=None):
        self.sd.send_message(message, code)
    
    def clear_memory(self):
        logger.info("Clearing memory")
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        gc.collect()