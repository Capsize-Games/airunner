import os
import torch
import gc

from airunner.aihandler.llm import LLM
from airunner.aihandler.logger import Logger as logger
from airunner.aihandler.runner import SDRunner
from airunner.aihandler.settings_manager import SettingsManager


class Engine:
    """
    The engine is responsible for processing requests and offloading
    them to the appropriate AI model controller.
    """
    model_type = None

    @property
    def hf_username(self):
        return self.sd.hf_username
    
    @property
    def hf_api_key_write_key(self):
        return self.sd.hf_api_key_write_key

    def __init__(self, **kwargs):
        self.app = kwargs.get("app", None)
        self.message_var = kwargs.get("message_var", None)
        self.message_handler = kwargs.get("message_handler", None)
        self.llm = LLM(app=self.app, engine=self)
        self.sd = SDRunner(
            app=self.app,
            message_var=self.message_var,
            message_handler=self.message_handler,
            engine=self
        )
        self.settings_manager = SettingsManager()

    def generator_sample(self, data: dict):
        """
        This function will determine if the request
        :param data:
        :return:
        """
        logger.info("generator_sample called")
        is_llm = self.is_llm_request(data)
        if is_llm and self.model_type != "llm":
            logger.info("Switching to LLM model")
            self.model_type = "llm"
            do_unload_model = self.settings_manager.unload_unused_model
            do_move_to_cpu = not do_unload_model and self.settings_manager.move_unused_model_to_cpu
            if do_move_to_cpu:
                self.sd.move_to_cpu()
                self.clear_memory()
            elif do_unload_model:
                self.sd.unload_model()
                self.sd.unload_tokenizer()
                self.clear_memory()
            # self.llm.move_to_device()
        elif not is_llm and self.model_type != "art":
            logger.info("Switching to art model")
            self.model_type = "art"
            self.unload_llm()

        if is_llm:
            logger.info("Engine calling llm.do_generate")
            self.llm.do_generate(data)
        else:
            logger.info("Engine calling sd.generator_sample")
            self.sd.generator_sample(data)

    def is_llm_request(self, data):
        return "llm_request" in data

    def unload_llm(self):
        """
        This function will either leave the LLM
        on the GPU, move it to the CPU or unload it.
        The choice is dependent on the current dtype
        and other settings such as use_gpu
        and whether or not the user has enough
        VRAM to keep the LLM loaded while
        using other models.
        """
        do_unload_model = self.settings_manager.unload_unused_model
        do_move_to_cpu = not do_unload_model and self.settings_manager.move_unused_model_to_cpu
        dtype = self.settings_manager.llm_generator_setting.dtype
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
        gc.collect()