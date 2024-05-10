from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class LLMRequestWorker(Worker):
    def handle_message(self, message):
        self.emit_signal(SignalCode.LLM_REQUEST_WORKER_RESPONSE_SIGNAL, message)

    def register_signals(self):
        self.register(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, self.on_llm_request_signal)

    def on_llm_request_signal(self, message: dict):
        self.add_to_queue(message)
