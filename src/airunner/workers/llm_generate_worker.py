from airunner.aihandler.llm.causal_lm_transfformer_base_handler import CausalLMTransformerBaseHandler
from airunner.settings import AVAILABLE_DTYPES
from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class LLMGenerateWorker(Worker):
    llm = None

    def __init__(self, *args, do_load_on_init: bool = False, **kwargs):
        self.do_load_on_init = do_load_on_init
        super().__init__(*args, **kwargs)

    def register_signals(self):
        self.llm = CausalLMTransformerBaseHandler(do_load_on_init=self.do_load_on_init)
        self.register(SignalCode.LLM_REQUEST_WORKER_RESPONSE_SIGNAL, self.on_llm_request_worker_response_signal)
        self.register(SignalCode.LLM_UNLOAD_SIGNAL, self.on_unload_llm_signal)

    def on_unload_llm_signal(self, message: dict):
        """
        This function will either 
        
        1. Leave the LLM on the GPU
        2. Move it to the CPU
        3. Unload it from memory

        The choice is dependent on the current dtype and other settings.
        """
        self.logger.debug("on_unload_llm_signal")
        dtype = message.get("dtype", self.settings['llm_generator_settings']["dtype"])
        do_unload_model = message.get("do_unload_model", self.settings["memory_settings"]["unload_unused_models"] or dtype in AVAILABLE_DTYPES)
        move_unused_model_to_cpu = message.get("move_unused_model_to_cpu", False)
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
        if callback:
            callback()

    def on_llm_request_worker_response_signal(self, message: dict):
        self.add_to_queue(message)

    def handle_message(self, message):
        self.llm.handle_request(message)

    def unload_llm(self):
        self.logger.debug("Unloading LLM")
        self.llm.unload()
