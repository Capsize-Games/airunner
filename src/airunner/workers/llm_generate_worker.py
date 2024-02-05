from airunner.aihandler.casual_lm_transfformer_base_handler import CasualLMTransformerBaseHandler
from airunner.aihandler.settings import AVAILABLE_DTYPES
from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class LLMGenerateWorker(Worker):
    def __init__(self, prefix="LLMGenerateWorker"):
        self.llm = CasualLMTransformerBaseHandler()
        super().__init__(prefix=prefix)
        self.register(SignalCode.LLM_REQUEST_WORKER_RESPONSE_SIGNAL, self.on_llm_request_worker_response_signal)
        self.register(SignalCode.LLM_UNLOAD_SIGNAL, self.on_unload_llm_signal)

    def on_unload_llm_signal(self, message):
        """
        This function will either 
        
        1. Leave the LLM on the GPU
        2. Move it to the CPU
        3. Unload it from memory

        The choice is dependent on the current dtype and other settings.
        """
        do_unload_model = message.get("do_unload_model", False)
        move_unused_model_to_cpu = message.get("move_unused_model_to_cpu", False)
        do_move_to_cpu = not do_unload_model and move_unused_model_to_cpu
        dtype = message.get("dtype", "")
        callback = message.get("callback", None)
        if dtype in AVAILABLE_DTYPES:
            do_unload_model = True
            do_move_to_cpu = False
        if do_move_to_cpu:
            self.logger.info("Moving LLM to CPU")
            self.llm.move_to_cpu()
        elif do_unload_model:
            self.llm.unload()
        if callback:
            callback()

    def on_llm_request_worker_response_signal(self, message):
        self.add_to_queue(message)

    def handle_message(self, message):
        self.llm.handle_request(message)
    
    def unload_llm(self):
        self.llm.unload()
