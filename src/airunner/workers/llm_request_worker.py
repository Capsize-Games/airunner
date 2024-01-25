from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class LLMRequestWorker(Worker):
    def __init__(self, prefix="LLMRequestWorker"):
        super().__init__(prefix=prefix)
        self.register(SignalCode.LLM_REQUEST_SIGNAL, self.on_llm_request_signal)
    
    def on_llm_request_signal(self, message):
        print("adding llm request to queue", message)
        self.add_to_queue(message)
    
    def handle_message(self, message):
        super().handle_message(message)
