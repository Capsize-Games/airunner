import threading
from typing import Dict, Optional

from airunner.handlers.llm.handler import LLMHandler
from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class LLMGenerateWorker(Worker):
    def __init__(self):
        self.llm = None
        super().__init__()
        for signal in (
            (SignalCode.LLM_REQUEST_WORKER_RESPONSE_SIGNAL, self.on_llm_request_worker_response_signal),
            (SignalCode.LLM_UNLOAD_SIGNAL, self.on_llm_on_unload_signal),
            (SignalCode.LLM_LOAD_SIGNAL, self.on_llm_load_model_signal),
            (SignalCode.LLM_CLEAR_HISTORY_SIGNAL, self.on_llm_clear_history_signal),
            (SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, self.on_llm_request_signal),
            (SignalCode.RAG_RELOAD_INDEX_SIGNAL, self.on_llm_reload_rag_index_signal),
            (SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL, self.on_llm_add_chatbot_response_to_history),
            (SignalCode.LOAD_CONVERSATION, self.on_llm_load_conversation),
            (SignalCode.INTERRUPT_PROCESS_SIGNAL, self.llm_on_interrupt_process_signal),
            (SignalCode.QUIT_APPLICATION, self.on_quit_application_signal),
        ):
            self.register(signal[0], signal[1])
        self._llm_thread = None

    def on_quit_application_signal(self):
        self.logger.debug("Quitting LLM")
        self.running = False
        if self.llm:
            self.llm.unload()
        if self._llm_thread is not None:
            self._llm_thread.join()

    def on_llm_request_worker_response_signal(self, message: dict):
        self.add_to_queue(message)

    def on_llm_on_unload_signal(self, data=None):
        data = data or {}
        self.logger.debug("Unloading LLM")
        self.llm.unload()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_llm_load_model_signal(self, data):
        self._load_llm_thread(data)

    def on_llm_clear_history_signal(self, data:Optional[Dict] = None):
        if self.llm:
            self.llm.clear_history(data)

    def on_llm_request_signal(self, message: dict):
        self.add_to_queue(message)

    def llm_on_interrupt_process_signal(self):
        if self.llm:
            self.llm.do_interrupt()

    def on_llm_reload_rag_index_signal(self):
        if self.llm:
            self.llm.reload_rag_engine()

    def on_llm_add_chatbot_response_to_history(self, message):
        self.llm.add_chatbot_response_to_history(message)

    def on_llm_load_conversation(self, message):
        try:
            self.llm.load_conversation(message)
        except Exception as e:
            self.logger.error(f"Error in on_load_conversation: {e}")

    def start_worker_thread(self):
        if self.application_settings.llm_enabled:
            self._load_llm_thread()

    def handle_message(self, message):
        self.llm.handle_request(message)

    def _load_llm_thread(self, data=None):
        self._llm_thread = threading.Thread(target=self._load_llm, args=(data,))
        self._llm_thread.start()

    def load(self):
        self._load_llm()

    def _load_llm(self, data=None):
        data = data or {}
        if self.llm is None:
            self.llm = LLMHandler()

        self.llm.load()

        callback = data.get("callback", None)
        if callback:
            callback(data)
