from typing import Dict, Optional, Type

from airunner.enums import SignalCode
from airunner.workers.worker import Worker
from airunner.settings import AIRUNNER_LLM_ON
from airunner.handlers.llm.llm_model_manager import LLMModelManager
from airunner.handlers.llm.openrouter_model_manager import (
    OpenRouterModelManager,
)
# from airunner.handlers.llm.gemma3_model_manager import Gemma3Manager
from airunner.enums import ModelService


class LLMGenerateWorker(Worker):
    def __init__(self, local_agent_class=None):
        self.local_agent_class = local_agent_class
        self.signal_handlers = {
            SignalCode.LLM_UNLOAD_SIGNAL: self.on_llm_on_unload_signal,
            SignalCode.LLM_LOAD_SIGNAL: self.on_llm_load_model_signal,
            SignalCode.LLM_CLEAR_HISTORY_SIGNAL: self.on_llm_clear_history_signal,
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: self.on_llm_request_signal,
            SignalCode.RAG_RELOAD_INDEX_SIGNAL: self.on_llm_reload_rag_index_signal,
            SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL: self.on_llm_add_chatbot_response_to_history,
            SignalCode.LOAD_CONVERSATION: self.on_llm_load_conversation,
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.llm_on_interrupt_process_signal,
            SignalCode.QUIT_APPLICATION: self.on_quit_application_signal,
            SignalCode.CONVERSATION_DELETED: self.on_conversation_deleted_signal,
            SignalCode.SECTION_CHANGED: self.on_section_changed_signal,
            SignalCode.WEB_BROWSER_PAGE_HTML: self.on_web_browser_page_html_signal,
            SignalCode.LLM_MODEL_CHANGED: self.on_llm_model_changed_signal,
        }
        self._openrouter_model_manager: Optional[OpenRouterModelManager] = None
        self._local_model_manager: Optional[LLMModelManager] = None
        # self._gemma3_model_manager: Optional[Gemma3Manager] = None
        self._model_manager: Optional[Type[LLMModelManager]] = None
        super().__init__()
        self._llm_thread = None

    @property
    def use_openrouter(self) -> bool:
        return (
            self.llm_generator_settings.model_service
            == ModelService.OPENROUTER.value
        )

    # @property
    # def use_gemma3(self) -> bool:
    #     # Check if the model path contains "gemma-3" to identify Gemma3 models
    #     model_path = self.llm_generator_settings.model_version or ""
    #     return "gemma-3" in model_path.lower()

    @property
    def openrouter_model_manager(self) -> OpenRouterModelManager:
        if not self._openrouter_model_manager:
            self._openrouter_model_manager = OpenRouterModelManager(
                local_agent_class=self.local_agent_class
            )
        return self._openrouter_model_manager

    @property
    def local_model_manager(self) -> LLMModelManager:
        if not self._local_model_manager:
            self._local_model_manager = LLMModelManager(
                local_agent_class=self.local_agent_class
            )
        return self._local_model_manager

    # @property
    # def gemma3_model_manager(self) -> Gemma3Manager:
    #     if not self._gemma3_model_manager:
    #         self._gemma3_model_manager = Gemma3Manager()
    #     return self._gemma3_model_manager

    @property
    def model_manager(self) -> Type[LLMModelManager]:
        if self._model_manager is None:
            if self.use_openrouter:
                self._model_manager = self.openrouter_model_manager
            # elif self.use_gemma3:
            #     self._model_manager = self.gemma3_model_manager
            else:
                self._model_manager = self.local_model_manager
        return self._model_manager

    def on_conversation_deleted_signal(self, data):
        self.model_manager.on_conversation_deleted(data)

    def on_section_changed_signal(self):
        self.model_manager.on_section_changed()

    def on_web_browser_page_html_signal(self, data):
        if self.model_manager:
            self.model_manager.on_web_browser_page_html(
                data.get("content", "")
            )

    def on_llm_model_changed_signal(self, data: Dict):
        # Reset the model manager to ensure it's re-evaluated on next access
        self._model_manager = None
        self.unload_llm()

    def on_quit_application_signal(self):
        self.logger.debug("Quitting LLM")
        self.running = False
        if self.model_manager:
            self.model_manager.unload()
        if self._llm_thread is not None:
            self._llm_thread.join()

    def on_llm_on_unload_signal(self, data: Optional[Dict] = None):
        self.unload_llm(data)

    def unload_llm(self, data: Optional[Dict] = None):
        if not self.model_manager:
            return
        data = data or {}
        self.model_manager.unload()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_llm_load_model_signal(self, data):
        # Reset model manager to ensure proper selection based on current settings
        self._model_manager = None
        self._load_llm(data)

    def on_llm_clear_history_signal(self, data: Optional[Dict] = None):
        if self.model_manager:
            self.model_manager.clear_history(data)

    def on_llm_request_signal(self, message: dict):
        self.add_to_queue(message)

    def llm_on_interrupt_process_signal(self):
        if self.model_manager:
            self.model_manager.do_interrupt()

    def on_llm_reload_rag_index_signal(self):
        if self.model_manager:
            self.model_manager.reload_rag_engine()

    def on_llm_add_chatbot_response_to_history(self, message):
        self.model_manager.add_chatbot_response_to_history(message)

    def on_llm_load_conversation(self, message):
        try:
            self.model_manager.load_conversation(message)
        except Exception as e:
            self.logger.error(f"Error in on_load_conversation: {e}")

    def start_worker_thread(self):
        if self.application_settings.llm_enabled or AIRUNNER_LLM_ON:
            self._load_llm()

    def handle_message(self, message):
        if self.model_manager:
            self.model_manager.handle_request(message)

    def load(self):
        self._load_llm()

    def _load_llm(self, data=None):
        data = data or {}
        if self.model_manager is not None:
            self.model_manager.load()
        callback = data.get("callback", None)
        if callback:
            callback(data)
