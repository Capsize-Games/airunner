from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class LLMRequestWorker(Worker):
    def __init__(self, prefix="LLMRequestWorker"):
        super().__init__(prefix=prefix)
        self.register(SignalCode.LLM_REQUEST_SIGNAL, self.on_llm_request_signal)
    
    def on_llm_request_signal(self, message):
        self.add_to_queue(message)

    def handle_message(self, message):
        self.emit(SignalCode.LLM_REQUEST_WORKER_RESPONSE_SIGNAL, message)