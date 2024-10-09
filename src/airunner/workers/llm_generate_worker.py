from airunner.handlers.llm.causal_lm_transformer_base_handler import CausalLMTransformerBaseHandler
from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class LLMGenerateWorker(Worker):
    def __init__(self, agent_options=None):
        self.llm = None
        self.agent_options = agent_options
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
        ):
            self.register(signal[0], signal[1])

    def on_llm_request_worker_response_signal(self, message: dict):
        self.add_to_queue(message)

    def on_llm_on_unload_signal(self, data):
        self.logger.debug("Unloading LLM")
        self.llm.unload()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_llm_load_model_signal(self, data):
        self.llm.load()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_llm_clear_history_signal(self):
        self.llm.clear_history()

    def on_llm_request_signal(self, message: dict):
        self.add_to_queue(message)

    def llm_on_interrupt_process_signal(self):
        self.llm.do_interrupt()

    def on_llm_reload_rag_index_signal(self):
        self.llm.reload_rag()

    def on_llm_add_chatbot_response_to_history(self, message):
        self.llm.add_chatbot_response_to_history(message)

    def on_llm_load_conversation(self, message):
        try:
            self.llm.load_conversation(message)
        except Exception as e:
            self.logger.error(f"Error in on_load_conversation: {e}")

    def start_worker_thread(self):
        self.llm = CausalLMTransformerBaseHandler(agent_options=self.agent_options)
        if self.application_settings.llm_enabled:
            self.llm.load()

    def handle_message(self, message):
        self.llm.handle_request(message)
