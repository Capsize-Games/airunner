"""Service-owned LLM generation worker."""

import os
import threading
import time
import uuid
from typing import Dict, Optional

from airunner_services.llm.workers.mixins import ModelDownloadMixin
from airunner_services.llm.workers.mixins import QuantizationMixin
from airunner_services.llm.workers.mixins import RAGIndexingMixin
from airunner_services.contract_enums import LLMActionType
from airunner_services.contract_enums import ModelService
from airunner_services.contract_enums import ModelStatus
from airunner_services.contract_enums import ModelType
from airunner_services.settings import AIRUNNER_LLM_ON
from airunner_services.llm.llm_response import LLMResponse
from airunner_services.model_management.llm_model_manager import (
    LLMModelManager,
)
from airunner_services.utils.application.enum_resolver import signal_code_proxy
from airunner_services.utils.application.runtime_primitives import QTimer
from airunner_services.workers.worker import Worker

SignalCode = signal_code_proxy(
    {
        "LLM_TEXT_STREAMED_SIGNAL": "llm_text_streamed_signal",
        "LLM_TEXT_GENERATE_REQUEST_SIGNAL": (
            "llm_text_generate_request_signal"
        ),
        "LLM_CLEAR_HISTORY_SIGNAL": ("llm_clear_history_signal"),
        "LLM_UNLOAD_SIGNAL": "llm_unload_signal",
        "LLM_LOAD_SIGNAL": "llm_load_signal",
        "RAG_INDEX_ALL_DOCUMENTS": ("rag_index_all_documents_signal"),
        "RAG_INDEX_SELECTED_DOCUMENTS": (
            "rag_index_selected_documents_signal"
        ),
        "RAG_INDEXING_PROGRESS": "rag_indexing_progress_signal",
        "RAG_INDEXING_COMPLETE": "rag_indexing_complete_signal",
        "RAG_INDEX_CANCEL": "rag_index_cancel_signal",
        "RAG_LOAD_EMBEDDING": "rag_load_embedding_signal",
    }
)


class LLMGenerateWorker(
    RAGIndexingMixin,
    QuantizationMixin,
    ModelDownloadMixin,
    Worker,
):
    """Orchestrate LLM requests, model loading, and retry behavior."""

    def __init__(self):
        """Initialize worker state and deferred LLM lifecycle helpers."""
        self.signal_handlers = {
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: (
                self.on_llm_request_signal
            ),
            SignalCode.LLM_CLEAR_HISTORY_SIGNAL: (
                self.on_llm_clear_history_signal
            ),
            SignalCode.LLM_UNLOAD_SIGNAL: (self.on_llm_on_unload_signal),
            SignalCode.LLM_LOAD_SIGNAL: (self.on_llm_load_model_signal),
            SignalCode.RAG_INDEX_ALL_DOCUMENTS: (
                self.on_rag_index_all_documents_signal
            ),
            SignalCode.RAG_INDEX_SELECTED_DOCUMENTS: (
                self.on_rag_index_selected_documents_signal
            ),
            SignalCode.RAG_INDEXING_PROGRESS: (
                self.on_rag_indexing_progress_signal
            ),
            SignalCode.RAG_INDEXING_COMPLETE: (
                self.on_rag_indexing_complete_signal
            ),
            SignalCode.RAG_INDEX_CANCEL: (self.on_rag_index_cancel_signal),
            SignalCode.RAG_LOAD_EMBEDDING: (self.on_rag_load_embedding_signal),
        }
        self._model_manager: Optional[LLMModelManager] = None
        self._model_manager_lock = threading.Lock()
        self._interrupted = False
        self._download_dialog_showing = False
        self._download_dialog = None
        self._pending_llm_request = None
        self._pending_unload_request: Optional[Dict] = None
        self.manager_thread: Optional[object] = None
        self.download_manager = None
        super().__init__()
        self._llm_thread = None

        self._last_request_time: Optional[float] = None
        self._inactivity_timer: Optional[object] = None
        self._inactivity_timeout = 300
        self._auto_unload_enabled = False

    @property
    def use_openrouter(self) -> bool:
        """Return whether the worker is configured for OpenRouter."""
        return (
            self.llm_generator_settings.model_service
            == ModelService.OPENROUTER.value
        )

    @property
    def use_ollama(self) -> bool:
        """Return whether the worker is configured for Ollama."""
        return (
            self.llm_generator_settings.model_service
            == ModelService.OLLAMA.value
        )

    @property
    def use_openai(self) -> bool:
        """Return whether the worker is configured for OpenAI."""
        return (
            self.llm_generator_settings.model_service
            == ModelService.OPENAI.value
        )

    @property
    def has_model_manager(self) -> bool:
        """Return whether the unified model manager is initialized."""
        return self._model_manager is not None

    def current_model_status(self) -> Optional[ModelStatus]:
        """Return the current local LLM status without creating a manager."""
        if self._model_manager is None:
            return None
        return self._model_manager.model_status.get(ModelType.LLM)

    @property
    def model_manager(self) -> LLMModelManager:
        """Return the shared model manager configured for the active backend."""
        with self._model_manager_lock:
            if self._model_manager is None:
                self._model_manager = LLMModelManager()

                db_api_key = (
                    getattr(self.llm_generator_settings, "api_key", None)
                    or None
                )
                db_api_base_url = (
                    getattr(self.llm_generator_settings, "api_base_url", None)
                    or None
                )
                if self.use_openrouter:
                    self._model_manager.llm_settings.use_local_llm = False
                    self._model_manager.llm_settings.use_openrouter = True
                    if db_api_key:
                        self._model_manager.llm_settings.openrouter_api_key = (
                            db_api_key
                        )
                elif self.use_ollama:
                    self._model_manager.llm_settings.use_local_llm = False
                    self._model_manager.llm_settings.use_ollama = True
                    if db_api_base_url:
                        self._model_manager.llm_settings.ollama_base_url = (
                            db_api_base_url
                        )
                elif self.use_openai:
                    self._model_manager.llm_settings.use_local_llm = False
                    self._model_manager.llm_settings.use_openai = True
                    if db_api_key:
                        self._model_manager.llm_settings.openai_api_key = (
                            db_api_key
                        )
                else:
                    self._model_manager.llm_settings.use_local_llm = True

            return self._model_manager

    @property
    def local_model_manager(self) -> LLMModelManager:
        """Return a model manager forced into local execution mode."""
        manager = LLMModelManager()
        manager.llm_settings.use_local_llm = True
        manager.llm_settings.use_openrouter = False
        manager.llm_settings.use_ollama = False
        return manager

    def on_conversation_deleted_signal(self, data: Dict) -> None:
        """Forward conversation deletion to the model manager."""
        self.model_manager.on_conversation_deleted(data)

    def on_section_changed_signal(self, data: Dict = None) -> None:
        """Forward section changes to the model manager."""
        self.model_manager.on_section_changed()

    def on_llm_model_changed_signal(self, data: Dict) -> None:
        """Unload only when a model change explicitly requests reload."""
        if not isinstance(data, dict) or not data.get("reload_runtime"):
            return

        if self._model_manager:
            self._model_manager.unload()

    def on_rag_load_documents_signal(self, data: Dict) -> None:
        """Load one document batch into the RAG engine."""
        self.logger.debug("Worker received RAG signal!")
        manager = self.model_manager
        self.logger.debug(
            f"Model manager ready (type: {type(manager).__name__})"
        )

        if data.get("clear_documents", False):
            self.logger.debug("Clearing RAG documents")
            self._clear_rag_documents()

        documents = data.get("documents", [])
        if documents:
            self.logger.debug(f"Loading {len(documents)} documents into RAG")
            self._load_documents_into_rag(documents)
            self.logger.info(f"✓ Loaded {len(documents)} documents into RAG")

    def _clear_rag_documents(self) -> None:
        """Clear all previously indexed RAG documents."""
        if hasattr(self.model_manager, "clear_rag_documents"):
            self.model_manager.clear_rag_documents()

    def _load_documents_into_rag(self, documents: list) -> None:
        """Load one iterable of documents into the RAG engine."""
        for doc in documents:
            try:
                if isinstance(doc, str) and os.path.exists(doc):
                    self.model_manager.load_file_into_rag(doc)
                    continue

                if isinstance(doc, (bytes, bytearray)):
                    self.model_manager.load_bytes_into_rag(
                        doc,
                        source_name="upload",
                        file_ext=".epub",
                    )
                    continue

                if isinstance(doc, dict) and "content" in doc:
                    file_type = doc.get("file_type", "")
                    content = doc.get("content")
                    if file_type.lower() in [".html", "html"]:
                        self.model_manager.load_file_into_rag(
                            content,
                            source_name=doc.get(
                                "source_name",
                                "web_content",
                            ),
                        )
                    elif file_type.lower() in [
                        ".epub",
                        "epub",
                        ".mobi",
                        "mobi",
                        ".pdf",
                        "pdf",
                    ]:
                        content_bytes = (
                            content
                            if isinstance(content, (bytes, bytearray))
                            else str(content).encode("utf-8")
                        )
                        normalized_ext = str(file_type).lower()
                        if not normalized_ext.startswith("."):
                            normalized_ext = f".{normalized_ext}"
                        self.model_manager.load_bytes_into_rag(
                            content_bytes,
                            source_name=doc.get(
                                "source_name",
                                f"{normalized_ext.removeprefix('.')}"
                                "_upload",
                            ),
                            file_ext=normalized_ext,
                        )
                    else:
                        self.model_manager.load_html_into_rag(
                            str(content),
                            source_name=doc.get(
                                "source_name",
                                "web_content",
                            ),
                        )
                    continue

                if isinstance(doc, str) and (
                    "<html" in doc.lower()
                    or "<body" in doc.lower()
                    or len(doc) > 100
                ):
                    self.model_manager.load_html_into_rag(doc)
                    continue

                self.model_manager.load_html_into_rag(str(doc))
            except Exception as error:
                self.logger.error(
                    f"Failed to load RAG document {repr(doc)}: {error}"
                )

    def _start_inactivity_timer(self) -> None:
        """Start the inactivity monitoring timer when auto-unload is on."""
        if not self._auto_unload_enabled:
            return

        self._inactivity_timer = QTimer()
        self._inactivity_timer.timeout.connect(self._check_inactivity)
        self._inactivity_timer.start(60000)
        self.logger.info("LLM auto-unload timer started (5 minute timeout)")

    def _check_inactivity(self) -> None:
        """Unload the model after extended inactivity when enabled."""
        if not self._auto_unload_enabled or not self._last_request_time:
            return

        if not self._model_manager or not self.has_model_manager:
            return

        if (
            self._model_manager.model_status.get(ModelType.LLM)
            != ModelStatus.LOADED
        ):
            return

        inactive_time = time.time() - self._last_request_time

        if inactive_time >= self._inactivity_timeout:
            self.logger.info(
                f"LLM model idle for {int(inactive_time/60)} minutes - auto-unloading"
            )
            self.unload_llm()
            self._last_request_time = None

    def _update_activity_timestamp(self) -> None:
        """Refresh the last-request timestamp for inactivity tracking."""
        self._last_request_time = time.time()

    def on_quit_application_signal(self, data: Optional[Dict] = None) -> None:
        """Unload the model and stop the worker during application shutdown."""
        self.logger.debug("Quitting LLM")
        self.running = False
        if self._model_manager:
            self._model_manager.unload()
        if self._llm_thread is not None:
            self._llm_thread.join()

    def on_llm_on_unload_signal(self, data: Optional[Dict] = None) -> None:
        """Handle one queued unload request."""
        self.unload_llm(data)

    def request_unload_after_interrupt(
        self,
        data: Optional[Dict] = None,
    ) -> bool:
        """Interrupt the current request and queue one unload."""
        if self._model_manager is None:
            return False

        request_data = dict(data or {})
        self.llm_on_interrupt_process_signal(request_data)
        self._pending_unload_request = request_data
        if self._pending_llm_request is None:
            self._queue_pending_unload_request()
        return True

    def _queue_pending_unload_request(self) -> None:
        """Queue any unload requested during or after interruption."""
        if self._pending_unload_request is None:
            return

        request_data = self._pending_unload_request
        self._pending_unload_request = None
        self.add_to_queue(
            {
                "_message_type": "llm_unload",
                "data": request_data,
            }
        )

    def unload_llm(self, data: Optional[Dict] = None) -> None:
        """Unload the LLM model and execute an optional callback."""
        if not self._model_manager:
            return
        data = data or {}
        self._model_manager.unload()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_llm_load_model_signal(self, data: Dict) -> None:
        """Handle a queued model-load request."""
        self._load_llm_thread(data)

    def on_llm_clear_history_signal(self, data: Optional[Dict] = None) -> None:
        """Forward the clear-history request to the model manager."""
        if self._model_manager:
            self._model_manager.clear_history(data)

    def on_llm_request_signal(self, message: dict) -> None:
        """Queue one incoming LLM request for generation."""
        self.logger.info(
            f"Received LLM request signal: {list(message.keys())}"
        )
        if self._interrupted:
            self.logger.info("Clearing interrupt flag - new message received")
            self._interrupted = False

        request_id = message.get("request_id") or str(uuid.uuid4())
        message["request_id"] = request_id
        if isinstance(message.get("request_data"), dict):
            message["request_data"].setdefault("request_id", request_id)
        self.logger.debug(
            f"Assigned request_id={request_id} to incoming request"
        )

        self._update_activity_timestamp()
        self.add_to_queue(message)
        self.logger.info("Added request to queue")

    def llm_on_interrupt_process_signal(self, data=None) -> None:
        """Interrupt the active generation and clear queued work."""
        self._interrupted = True
        self.clear_queue()
        self.logger.info("Interrupted and cleared LLM generation queue")

        if hasattr(self, "_model_manager") and self._model_manager is not None:
            self.logger.info(
                f"Calling do_interrupt on model_manager {id(self._model_manager)}"
            )
            try:
                self._model_manager.do_interrupt()
            except Exception as error:
                self.logger.error(
                    f"Error calling do_interrupt(): {error}",
                    exc_info=True,
                )
        else:
            self.logger.warning("Model manager not available for interrupt")

    def on_llm_add_chatbot_response_to_history(self, message: Dict) -> None:
        """Add one chatbot response to the conversation history."""
        self.model_manager.add_chatbot_response_to_history(message)

    def on_llm_load_conversation(self, message: Dict) -> None:
        """Load one conversation into the model manager."""
        try:
            self.model_manager.load_conversation(message)
        except Exception as error:
            self.logger.error(f"Error in on_load_conversation: {error}")

    def start_worker_thread(self) -> None:
        """Start the worker thread if LLM is enabled."""
        if self.application_settings.llm_enabled or AIRUNNER_LLM_ON:
            self._load_llm_thread()

    def handle_message(self, message: Dict) -> None:
        """Process queued messages for LLM generation.

        Runs on the worker's own thread, which does not inherit the
        request context vars. Re-apply the tenant captured at dispatch
        time so conversation persistence targets the caller's schema
        instead of the anonymous one. ``tenant_scope`` always restores
        the previous key, preventing leakage between tenants on this
        long-lived thread.
        """
        from airunner_services.data.tenant import tenant_scope

        with tenant_scope(
            message.get("tenant_key") if isinstance(message, dict) else None
        ):
            self._handle_message(message)

    def _handle_message(self, message: Dict) -> None:
        """Dispatch one queued worker payload (tenant context applied)."""
        message_type = message.get("_message_type")
        if message_type == "llm_load":
            self.on_llm_load_model_signal(message.get("data", {}))
            return
        if message_type == "llm_unload":
            self.on_llm_on_unload_signal(message.get("data", {}))
            return

        if message.get("_message_type") == "download_complete":
            self.logger.info("Processing download complete message from queue")
            self.on_huggingface_download_complete_signal(
                message.get("data", {})
            )
            return

        if self._interrupted:
            self.logger.info("Skipping message - worker interrupted")
            return

        self.logger.info(
            f"handle_message called with keys: {list(message.keys())}"
        )
        self.logger.info(f"request_id in message: {message.get('request_id')}")

        self._pending_llm_request = message
        self.logger.info(
            f"Stored pending request with ID: {message.get('request_id')}"
        )

        manager = self.model_manager
        request_data = message.get("request_data", {})
        llm_request = request_data.get("llm_request")

        if (
            llm_request.rag_files is not None
            and len(llm_request.rag_files) > 0
        ):
            self.logger.info(
                f"Auto-loading {len(llm_request.rag_files)} RAG documents from request"
            )
            self._load_documents_into_rag(llm_request.rag_files)

        try:
            result = manager.handle_request(message, {})
        except Exception as error:
            self._pending_llm_request = None
            self.logger.exception(f"LLM request failed: {error}")
            try:
                request_id = message.get("request_id")
                action = None
                try:
                    action = message.get("request_data", {}).get("action")
                except Exception:
                    action = None

                action_val = (
                    action
                    if isinstance(action, LLMActionType)
                    else LLMActionType.CHAT
                )

                response = LLMResponse(
                    message=f"Error invoking LLM: {error}",
                    is_first_message=True,
                    is_end_of_message=True,
                    sequence_number=0,
                    action=action_val,
                    request_id=request_id,
                    is_system_message=True,
                )
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    {"response": response, "request_id": request_id},
                )
            except Exception:
                pass
            self._queue_pending_unload_request()
            return

        if result:
            response_text = result.get("response", "")
            retry_after_download = bool(result.get("retry_after_download"))
            has_error = result.get("error") or (
                isinstance(response_text, str)
                and response_text.startswith("Error:")
            )

            if not has_error:
                self.logger.info(
                    "Request completed successfully, clearing pending request"
                )
                self._pending_llm_request = None
            elif retry_after_download:
                self.logger.info(
                    "Request failed while model download is still pending; "
                    "keeping pending request for automatic retry"
                )
            else:
                self._pending_llm_request = None
                self.logger.info(
                    "Request failed with non-retryable error, clearing pending request"
                )

                try:
                    request_id = message.get("request_id")
                    action = None
                    try:
                        action = message.get("request_data", {}).get("action")
                    except Exception:
                        action = None
                    action_val = (
                        action
                        if isinstance(action, LLMActionType)
                        else LLMActionType.CHAT
                    )

                    response_message = response_text or "Error invoking LLM"
                    if not isinstance(response_message, str):
                        response_message = str(response_message)

                    response = LLMResponse(
                        message=response_message,
                        is_first_message=True,
                        is_end_of_message=True,
                        sequence_number=0,
                        action=action_val,
                        request_id=request_id,
                        is_system_message=True,
                    )
                    self.emit_signal(
                        SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                        {"response": response, "request_id": request_id},
                    )
                except Exception:
                    pass

            self._queue_pending_unload_request()

    def _load_llm_thread(self, data: Optional[Dict] = None) -> None:
        """Load the LLM in a separate background thread."""
        self._llm_thread = threading.Thread(
            target=self._load_llm,
            args=(data,),
        )
        self._llm_thread.start()

    def load(self) -> None:
        """Load the LLM model synchronously."""
        self._load_llm()

    def _load_llm(self, data: Optional[Dict] = None) -> None:
        """Load the LLM model and execute an optional callback."""
        data = data or {}
        self.model_manager.load()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def unload(self, data: Optional[Dict] = None) -> None:
        """Unload the LLM model and free its resources."""
        self.unload_llm(data)
