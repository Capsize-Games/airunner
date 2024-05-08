import queue

from PySide6.QtCore import QThread

from airunner.aihandler.llm.causal_lm_transfformer_base_handler import CausalLMTransformerBaseHandler
from airunner.settings import AVAILABLE_DTYPES, SLEEP_TIME_IN_MS
from airunner.enums import QueueType
from airunner.workers.worker import Worker


class LLMGenerateWorker(Worker):
    llm = None

    def __init__(self, *args, do_load_on_init: bool = False, **kwargs):
        self.do_load_on_init = do_load_on_init
        super().__init__(*args, **kwargs)
        self.llm = CausalLMTransformerBaseHandler(do_load_on_init=self.do_load_on_init)

    def on_unload_llm_signal(self, message: dict):
        """
        This function will either 
        
        1. Leave the LLM on the GPU
        2. Move it to the CPU
        3. Unload it from memory

        The choice is dependent on the current dtype and other settings.
        """
        dtype = self.settings["llm_generator_settings"]["dtype"]
        do_unload_model = self.settings["memory_settings"]["unload_unused_models"]
        move_unused_model_to_cpu = self.settings["memory_settings"]["move_unused_model_to_cpu"]
        do_move_to_cpu = not do_unload_model and move_unused_model_to_cpu
        callback = message.get("callback", None)
        if dtype in AVAILABLE_DTYPES:
            do_unload_model = True
            do_move_to_cpu = False
        if do_move_to_cpu:
            self.logger.debug("Moving LLM to CPU")
            self.llm.move_to_cpu()
        elif do_unload_model:
            self.unload_llm()
        print(callback)
        if callback:
            callback()

    def run(self):
        if self.queue_type == QueueType.NONE:
            return
        self.logger.debug("Starting")
        self.running = True
        while self.running:
            self.preprocess()
            try:
                msg = self.get_item_from_queue()
                if msg is not None:
                    self.handle_message(msg)
            except queue.Empty:
                msg = None
            if self.paused:
                self.logger.debug("Paused")
                while self.paused:
                    QThread.msleep(SLEEP_TIME_IN_MS)
                self.logger.debug("Resumed")
            QThread.msleep(SLEEP_TIME_IN_MS)

    def llm_load_signal(self, data: dict):
        print("llm_load_signal called from nats with", data)

    def on_llm_request_worker_response_signal(self, message: dict):
        self.add_to_queue(message)

    def handle_message(self, message):
        # try:
        self.llm.handle_request(message)
        # except Exception as e:
        #     self.logger.error(f"Error in handle_message: {e}")
        #     self.logger.error(f"Message: {message}")

    def unload_llm(self):
        self.logger.debug("Unloading LLM")
        self.llm.unload()
