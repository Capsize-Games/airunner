import queue

from PySide6.QtCore import QObject, Signal, Slot

from airunner.enums import QueueType, SignalCode, ModelType, ModelStatus
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.utils.clear_memory import clear_memory
from airunner.workers.worker import Worker
from PySide6.QtCore import QThread


class LLMGenerateWorker(Worker):
    def __init__(self, prefix=None, do_load_on_init=False, agent_class=None, agent_options=None):
        self.llm = None
        self.do_load_on_init = do_load_on_init
        self.agent_class = agent_class
        self.agent_options = agent_options
        super().__init__(prefix=prefix)

    def add_chatbot_response_to_history(self, message):
        self.llm.chat_agent.add_chatbot_response_to_history(message)

    def on_load_conversation(self, message):
        try:
            self.llm.chat_agent.on_load_conversation(message)
        except Exception as e:
            self.logger.error(f"Error in on_load_conversation: {e}")

    def on_reload_rag_index_signal(self, data: dict = None):
        self.llm.chat_agent.reload_rag(data)

    def on_unload_llm_signal(self, _message):
        if self.llm:
            self.llm.unload()

    def handle_error(self, error_message):
        print(f"Error: {error_message}")

    def on_load_model_signal(self):
        if self.llm:
            self.llm.on_load_model_signal()

    def on_clear_history_signal(self):
        if self.llm:
            self.llm.on_clear_history_signal()

    def on_interrupt_process_signal(self):
        if self.llm:
            self.llm.on_interrupt_process_signal()

    def start_worker_thread(self):
        from airunner.aihandler.llm.causal_lm_transformer_base_handler import CausalLMTransformerBaseHandler

        if self.application_settings.llm_enabled:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.LLM,
                    "status": ModelStatus.LOADING,
                    "path": ""
                }
            )
        self.llm = CausalLMTransformerBaseHandler(
            agent_class=self.agent_class,
            do_load_on_init=self.do_load_on_init,
            agent_options=self.agent_options
        )

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

    def llm_load_signal(self, data: dict):
        print("llm_load_signal called from nats with", data)

    def on_llm_request_worker_response_signal(self, message: dict):
        self.add_to_queue(message)

    def handle_message(self, message):
        if self.llm:
            # try:
            self.llm.handle_request(message)
            # except Exception as e:
            #     self.logger.error(f"Error in handle_message: {e}")
            #     self.logger.error(f"Message: {message}")

    def unload_llm(self):
        self.logger.debug("Unloading LLM")
        if self.llm:
            self.llm.unload()
            del self.llm
            self.llm = None
            clear_memory(clear_memory(self.memory_settings.default_gpu_llm))
