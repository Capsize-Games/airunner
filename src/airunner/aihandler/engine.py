import re
import threading
import torch
import traceback
import gc
from airunner.aihandler.enums import MessageCode
from airunner.aihandler.image_processor import ImageProcessor

from airunner.aihandler.llm import LLM
from airunner.aihandler.logger import Logger
from airunner.aihandler.runner import SDRunner
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

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
    model_type = None
    hear_signal = pyqtSignal(str)
    request_data = None
    llm = None
    sd = None
    tts = None
    stt = None
    ocr = None

    pyqtSlot(str)
    def hear(self, message):
        """
        This is a slot function for the hear_signal.
        The hear signal is triggered from the speech_to_text.listen function.
        """
        self.app.respond_to_voice(heard=message)

    def __init__(self, **kwargs):
        super().__init__()
        self.app = kwargs.get("app", None)
        self.message_var = kwargs.get("message_var", None)
        self.message_handler = kwargs.get("message_handler", None)
        self.clear_memory()
        self.initialize_llm()  # Large language model
        self.initialize_sd()   # Art model
        self.initialize_tts()  # Text to speech model (voice)
        # self.initialize_stt()  # Speech to text model (ears)
        # self.initialize_ocr()  # Vision to text model (eyes)
    
    def initialize_llm(self):
        """
        Initialize the LLM.
        """
        self.llm = LLM(app=self.app, engine=self)
    
    def initialize_sd(self):
        """
        Initialize Stable Diffusion.
        """
        self.sd = SDRunner(
            app=self.app,
            message_var=self.message_var,
            message_handler=self.message_handler,
            engine=self
        )

    def initialize_stt(self):
        """
        Initialize speech to text.
        """
        self.stt = SpeechToText(
            hear_signal=self.hear_signal,
            engine=self,
            duration=10.0,
            fs=16000
        )
        self.hear_signal.connect(self.hear)
        # self.listen_thread = threading.Thread(target=self.stt.listen)
        # self.listen_thread.start()
    
    def initialize_tts(self):
        """
        Initialize text to speech.
        """
        tts_settings = self.app.settings["tts_settings"]
        self.tts = TTS(engine=self)
        self.tts_thread = threading.Thread(target=self.tts.run)
        self.tts_thread.start()

    def initialize_ocr(self):
        """
        Initialize vision to text.
        """
        self.ocr = ImageProcessor(engine=self)

    def move_pipe_to_cpu(self):
        Logger.info("Moving pipe to CPU")
        self.sd.move_pipe_to_cpu()
        self.clear_memory()
    
    def generator_sample(self, data: dict):
        """
        This function will determine if the request
        :param data:
        :return:
        """
        Logger.info("generator_sample called")
        self.llm_generator_sample(data)
        self.tts_generator_sample(data)
        self.sd_generator_sample(data)
    
    def llm_generator_sample(self, data: dict):
        if "llm_request" not in data or not self.llm:
            return
        if self.model_type != "llm":
            Logger.info("Preparing LLM model...")
            # if self.tts:
            #     self.tts.move_model(to_cpu=False)
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
        Logger.info("Engine calling llm.do_generate")
        self.llm.do_generate(data)
    
    def tts_generator_sample(self, data: dict):
        if "tts_request" not in data or not self.tts:
            return
        Logger.info("Preparing TTS model...")
        # self.tts.move_model(to_cpu=False)
        signal = data["request_data"].get("signal", None)
        message_object = data["request_data"].get("message_object", None)
        is_bot = data["request_data"].get("is_bot", False)
        first_message = data["request_data"].get("first_message", None)
        last_message = data["request_data"].get("last_message", None)
        if data["request_data"]["tts_settings"]["enable_tts"]:
            text = data["request_data"]["text"]
            # check if ends with a proper sentence ender, if not, add a period
            if not text.endswith((".", "?", "!", "...", "-", "—", )):
                text += "."
            generator = self.tts.add_text(text, "a", data["request_data"]["tts_settings"])
            for success in generator:
                if signal and success:
                    signal.emit(message_object, is_bot, first_message, last_message)

    def sd_generator_sample(self, data:dict):
        if "sd_request" not in data or not self.sd:
            return
        if self.model_type != "art":
            Logger.info("Preparing Art model...")
            do_unload_model = data["options"].get("unload_unused_model", False)
            move_unused_model_to_cpu = data["options"].get("move_unused_model_to_cpu", False)
            self.model_type = "art"
            self.do_unload_llm(data["request_data"], do_unload_model, move_unused_model_to_cpu)
        Logger.info("Engine calling sd.generator_sample")
        self.sd.generator_sample(data)

    def do_listen(self):
        # self.stt.do_listen()
        pass

    def unload_llm(self, request_data: dict, do_unload_model: bool, move_unused_model_to_cpu: bool):
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
        if request_data:
            dtype = self.app.settings["llm_generator_settings"]["dtype"]
            if dtype in ["2bit", "4bit", "8bit"]:
                do_unload_model = True
                do_move_to_cpu = False

        if do_move_to_cpu:
            Logger.info("Moving LLM to CPU")
            self.llm.move_to_cpu()
            self.clear_memory()
        elif do_unload_model:
            self.do_unload_llm()
    
    def do_unload_llm(self):
        Logger.info("Unloading LLM")
        self.llm.unload_model()
        self.llm.unload_tokenizer()
        self.clear_memory()

    def cancel(self):
        """
        Cancel Stable Diffusion request.
        """
        self.sd.cancel()
    
    def unload_stablediffusion(self):
        """
        Unload the Stable Diffusion model from memory.
        """
        self.sd.unload()
    
    def handle_message_code(self, message, code):
        code = code or MessageCode.STATUS
        if code == MessageCode.ERROR:
            traceback.print_stack()
            Logger.error(message)
        elif code == MessageCode.WARNING:
            Logger.warning(message)
        elif code == MessageCode.STATUS:
            Logger.info(message)

    message = ""
    first_message = True

    def send_message(self, message, code=None):
        """
        Send a message to the Stable Diffusion model.
        """
        self.handle_message_code(message, code)
        
        if code == MessageCode.TEXT_GENERATED:
            message = self.parse_message(message)
            self.message_var.emit({
                "code": MessageCode.ADD_TO_CONVERSATION,
                "message": dict(
                    name=self.app.settings["llm_generator_settings"]["botname"],
                    text=message,
                    is_bot=True,
                )
            })
        if code == MessageCode.TEXT_STREAMED:
            self.message += message
            self.current_message += message
            self.message = self.message.replace("</s>", "")
            self.current_message = self.current_message.replace("</s>", "")

            
            # check if sentence enders are in self.current_message
            is_end_of_sentence = False
            for ender in (".", "?", "!", "...", "-", "—", ):
                if ender in self.current_message:
                    is_end_of_sentence = True
                    break
            is_end_of_message = "</s>" in message
            self.tts.add_text(message.replace("</s>", ""), is_end_of_message=is_end_of_message)
            self.message_var.emit(dict(
                code=MessageCode.ADD_TO_CONVERSATION,
                message=dict(
                    name=self.app.settings["llm_generator_settings"]["botname"],
                    text=message.replace("</s>", ""),
                    is_bot=True,
                    first_message=self.first_message,
                    last_message=is_end_of_message
                )
            ))
            self.first_message = False
            if is_end_of_message:
                self.first_message = True
                self.message = ""
                self.current_message = ""

            # if is_end_of_sentence and not is_end_of_message:
            #     # split on all sentence enders
            #     sentences = re.split(r"(\.|\?|\!|\.\.\.|\-|\—)", self.current_message)
            #     # remove empty strings
            #     sentences = [s for s in sentences if s]
            #     # send to tts
            #     print("SENDING TO TTS via sentences[0]", sentences[0])
            #     self.handle_tts(sentences[0].strip())
            #     # remove the first sentence from the current message
            #     self.current_message = "".join(sentences[1:])
            # elif is_end_of_message:
            #     print("SENDING TO TTS via self.current_message", self.current_message)
            #     self.handle_tts(self.current_message.strip())
            #     self.message_var.emit({
            #         "code": MessageCode.ADD_TO_CONVERSATION,
            #         "message": dict(
            #             name=self.app.settings["llm_generator_settings"]["botname"],
            #             text=self.message,
            #             is_bot=True,
            #         )
            #     })
            #     self.message = ""
            #     self.current_message = ""
    
    current_message = ""

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
            # self.app.client.message = dict(
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
            self.tts.add_text(message)
    
    def clear_memory(self):
        """
        Clear the GPU ram.
        """
        Logger.info("Clearing memory")
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        gc.collect()
    
    def clear_llm_history(self):
        if self.llm:
            self.llm.clear_history()