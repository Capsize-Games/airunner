import threading
from typing import Dict, Optional, Type

from airunner.enums import SignalCode, ModelService, LLMActionType
from airunner.components.llm.managers.ollama_model_manager import (
    OllamaModelManager,
)
from airunner.components.application.workers.worker import Worker
from airunner.settings import AIRUNNER_LLM_ON
from airunner.components.llm.managers.llm_model_manager import LLMModelManager
from airunner.components.llm.managers.openrouter_model_manager import (
    OpenRouterModelManager,
)
from airunner.components.context.context_manager import ContextManager
from airunner.components.documents.data.models.document import (
    Document as DBDocument,
)
import uuid

# from airunner.handlers.llm.gemma3_model_manager import Gemma3Manager


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
            SignalCode.LLM_MODEL_CHANGED: self.on_llm_model_changed_signal,
            SignalCode.RAG_LOAD_DOCUMENTS: self.on_rag_load_documents_signal,
            SignalCode.INDEX_DOCUMENT: self.on_index_document_signal,
            SignalCode.MAP_SEARCH_REQUEST_SIGNAL: self.on_map_search_request_signal,  # Handle map search requests
        }
        self.context_manager = ContextManager()
        self._openrouter_model_manager: Optional[OpenRouterModelManager] = None
        self._ollama_model_manager: Optional[OllamaModelManager] = None
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

    @property
    def use_ollama(self) -> bool:
        return (
            self.llm_generator_settings.model_service
            == ModelService.OLLAMA.value
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
    def ollama_model_manager(self) -> OllamaModelManager:
        if not self._ollama_model_manager:
            self._ollama_model_manager = OllamaModelManager(
                local_agent_class=self.local_agent_class
            )
        return self._ollama_model_manager

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
            elif self.use_ollama:
                self._model_manager = self.ollama_model_manager
            # elif self.use_gemma3:
            #     self._model_manager = self.gemma3_model_manager
            else:
                self._model_manager = self.local_model_manager
        return self._model_manager

    def on_conversation_deleted_signal(self, data):
        self.model_manager.on_conversation_deleted(data)

    def on_section_changed_signal(self):
        self.model_manager.on_section_changed()

    def on_llm_model_changed_signal(self, data: Dict):
        # Reset the model manager to ensure it's re-evaluated on next access
        self._model_manager = None
        self.unload_llm()

    def on_rag_load_documents_signal(self, data: Dict):
        """
        Handle the signal to load documents into the RAG engine.
        This method is called when the RAG engine needs to load new documents.
        """
        if self.model_manager and self.model_manager.agent:
            if data.get("clear_documents", False):
                # Clear all previous RAG documents before loading new ones
                if hasattr(self.model_manager.agent, "clear_rag_documents"):
                    self.model_manager.agent.clear_rag_documents()
            documents = data.get("documents", [])
            if documents:
                # Call the RAGMixin's load_html_into_rag for each document string
                for doc in documents:
                    self.model_manager.agent.load_html_into_rag(doc)

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
        self._load_llm_thread(data)

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

    def on_index_document_signal(self, data: Dict):
        """
        Handle the INDEX_DOCUMENT signal: index the file by path, save the index, update DB, and release memory.
        """
        document_path = data.get("path", None)
        if not isinstance(document_path, str) or not document_path:
            return

        if not self.model_manager or not self.model_manager.agent:
            self.load()
        if not self.model_manager or not self.model_manager.agent:
            return
        try:
            agent = self.model_manager.agent
            agent.document_reader = None
            agent.target_files = [document_path]
            agent._load_index_from_documents()
            # Generate a UUID for this document's index
            index_uuid = str(uuid.uuid4())
            saved_uuid = agent._save_index_to_disc(
                document_path=document_path, index_uuid=index_uuid
            )
            db_docs = DBDocument.objects.filter_by(path=document_path)
            if db_docs and len(db_docs) > 0:
                db_doc = db_docs[0]
                db_doc.indexed = True
                db_doc.index_uuid = saved_uuid
                DBDocument.objects.update(
                    pk=db_doc.id, indexed=True, index_uuid=saved_uuid
                )
            agent.document_reader = None
            agent.index = None
            self.emit_signal(
                SignalCode.DOCUMENT_INDEXED, {"path": document_path}
            )
        except Exception as e:
            pass

    def on_map_search_request_signal(self, data: dict) -> None:
        print(
            f"[LLMGenerateWorker] on_map_search_request_signal called with data: {data}"
        )
        # Only process if this is a new query, not a result
        if not data or "query" not in data or not data["query"]:
            print(
                "[LLMGenerateWorker] Ignoring MAP_SEARCH_REQUEST_SIGNAL with no query."
            )
            return
        query = data.get("query", "")
        self._llm_agent_map_search(query)

    def _llm_agent_map_search(self, query: str) -> None:
        print(
            f"[LLMGenerateWorker] _llm_agent_map_search called with query: {query}"
        )
        if not self.model_manager or not hasattr(self.model_manager, "agent"):
            print("[LLMGenerateWorker] No model_manager or agent available.")
            return
        agent = self.model_manager.agent
        print(f"[LLMGenerateWorker] Using agent: {agent}")
        # Let the LLM agent reason about the action/tool to use
        print(
            f"[LLMGenerateWorker] map_search: calling agent._perform_tool_call with action={LLMActionType.MAP_TOOL}, query={query}"
        )
        result = agent._perform_tool_call(
            LLMActionType.MAP_TOOL,
            query=query,
        )
        print(f"[LLMGenerateWorker] agent._perform_tool_call result: {result}")

        # Check if the react_tool_agent has stored map tool result data
        print(f"[LLMGenerateWorker] Checking for stored map result...")
        print(
            f"[LLMGenerateWorker] Agent has react_tool_agent: {hasattr(agent, 'react_tool_agent')}"
        )
        if hasattr(agent, "react_tool_agent"):
            print(
                f"[LLMGenerateWorker] react_tool_agent: {agent.react_tool_agent}"
            )
            print(
                f"[LLMGenerateWorker] react_tool_agent has chat_engine: {hasattr(agent.react_tool_agent, 'chat_engine')}"
            )
            if hasattr(agent.react_tool_agent, "chat_engine"):
                print(
                    f"[LLMGenerateWorker] chat_engine has _last_map_tool_result: {hasattr(agent.react_tool_agent.chat_engine, '_last_map_tool_result')}"
                )
                if hasattr(
                    agent.react_tool_agent.chat_engine, "_last_map_tool_result"
                ):
                    print(
                        f"[LLMGenerateWorker] _last_map_tool_result value: {agent.react_tool_agent.chat_engine._last_map_tool_result}"
                    )

        if (
            hasattr(agent, "react_tool_agent")
            and hasattr(agent.react_tool_agent, "chat_engine")
            and hasattr(
                agent.react_tool_agent.chat_engine, "_last_map_tool_result"
            )
            and agent.react_tool_agent.chat_engine._last_map_tool_result
        ):
            print(
                f"[LLMGenerateWorker] Found stored map tool result: {agent.react_tool_agent.chat_engine._last_map_tool_result}"
            )
            result_obj = (
                agent.react_tool_agent.chat_engine._last_map_tool_result
            )
            # Clean up the stored result
            delattr(
                agent.react_tool_agent.chat_engine, "_last_map_tool_result"
            )
        else:
            # Use raw_output for map data, fallback to content for errors
            if hasattr(result, "raw_output") and result.raw_output:
                result_obj = result.raw_output
            else:
                result_obj = (
                    result.content if hasattr(result, "content") else result
                )
        # If result_obj is a string that looks like a dict, parse it
        if (
            isinstance(result_obj, str)
            and result_obj.startswith("{")
            and result_obj.endswith("}")
        ):
            import ast

            try:
                result_obj = ast.literal_eval(result_obj)
            except Exception:
                pass
        payload = {"result": result_obj}
        print(
            f"[LLMGenerateWorker] Emitting MAP_SEARCH_RESULT_SIGNAL with payload: {payload}"
        )
        self.emit_signal(
            SignalCode.MAP_SEARCH_RESULT_SIGNAL,
            payload,
        )

    def start_worker_thread(self):
        if self.application_settings.llm_enabled or AIRUNNER_LLM_ON:
            self._load_llm_thread()

    def handle_message(self, message):
        if self.model_manager:
            self.model_manager.handle_request(
                message, self.context_manager.all_contexts()
            )

    def _load_llm_thread(self, data=None):
        self._llm_thread = threading.Thread(
            target=self._load_llm, args=(data,)
        )
        self._llm_thread.start()

    def load(self):
        self._load_llm()

    def _load_llm(self, data=None):
        data = data or {}
        if self.model_manager is not None:
            self.model_manager.load()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def unload(self, data: Optional[Dict] = None):
        """
        Unload the LLM model and free VRAM/resources. This method is required for model load balancing.
        """
        self.unload_llm(data)
