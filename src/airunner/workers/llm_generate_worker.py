import queue

from airunner.enums import QueueType, SignalCode, ModelType, ModelStatus
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.utils.clear_memory import clear_memory
from airunner.workers.worker import Worker
from PySide6.QtCore import QThread


class LLMGenerateWorker(Worker):
    def __init__(self, prefix=None, do_load_on_init=False, agent_options=None):
        self.llm = None
        self.do_load_on_init = do_load_on_init
        self.agent_options = agent_options
        super().__init__(prefix=prefix)

    def add_chatbot_response_to_history(self, message):
        self.llm.add_chatbot_response_to_history(message)

    def on_load_conversation(self, message):
        try:
            self.llm.load_conversation(message)
        except Exception as e:
            self.logger.error(f"Error in on_load_conversation: {e}")

    def on_reload_rag_index_signal(self):
        if self.llm:
            self.llm.reload_rag()

    def on_unload_llm_signal(self, _message):
        if self.llm:
            self.llm.unload()

    def handle_error(self, error_message):
        print(f"Error: {error_message}")

    def on_load_model_signal(self):
        if self.llm:
            self.llm.load_llm()

    def on_clear_history_signal(self):
        if self.llm:
            self.llm.clear_history()

    def on_interrupt_process_signal(self):
        if self.llm:
            self.llm.do_interrupt()

    def on_llm_request_worker_response_signal(self, message: dict):
        self.add_to_queue(message)

    def start_worker_thread(self):
        if self.application_settings.llm_enabled:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.LLM,
                    "status": ModelStatus.LOADING,
                    "path": ""
                }
            )
        self.load_llm(do_load_on_init=self.do_load_on_init)

    def load_llm(self, do_load_on_init: bool = False):
        from airunner.aihandler.llm.causal_lm_transformer_base_handler import CausalLMTransformerBaseHandler
        self.llm = CausalLMTransformerBaseHandler(
            do_load_on_init=do_load_on_init,
            agent_options=self.agent_options
        )

    def unload_llm(self):
        self.logger.debug("Unloading LLM")
        if self.llm:
            self.llm.unload()
            del self.llm
            self.llm = None
            clear_memory(clear_memory(self.memory_settings.default_gpu_llm))
            self.load_llm()

    def run(self):
        if self.queue_type == QueueType.NONE:
            return
        self.logger.debug("Starting LLM generate worker")
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

    def handle_message(self, message):
        if self.llm:
            # try:
            self.llm.handle_request(message)
            # except Exception as e:
            #     self.logger.error(f"Error in handle_message: {e}")
            #     self.logger.error(f"Message: {message}")
