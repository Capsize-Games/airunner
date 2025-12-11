"""LLM generation worker with signal-based coordination."""

import threading
import time
from typing import Dict, Optional
import os
import uuid
from PySide6.QtCore import QThread, QTimer

from airunner.enums import ModelService, SignalCode, LLMActionType
from airunner.components.application.workers.worker import Worker
from airunner.settings import AIRUNNER_LLM_ON
from airunner.components.llm.managers.llm_model_manager import LLMModelManager
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.components.context.context_manager import ContextManager
from airunner.components.llm.workers.mixins import (
    RAGIndexingMixin,
    FineTuningMixin,
    QuantizationMixin,
    ModelDownloadMixin,
)


class LLMGenerateWorker(
    RAGIndexingMixin,
    FineTuningMixin,
    QuantizationMixin,
    ModelDownloadMixin,
    Worker,
):
    """Orchestrates LLM generation requests and model lifecycle.

    This worker handles:
    - LLM text generation requests
    - Model loading/unloading
    - RAG document indexing (via RAGIndexingMixin)
    - Fine-tuning operations (via FineTuningMixin)
    - Quantization settings (via QuantizationMixin)
    - Model downloads (via ModelDownloadMixin)

    Uses mixins for separation of concerns - each mixin handles
    a distinct functional area while this class provides core
    coordination and request handling.
    """

    def __init__(self):
        """Initialize worker with signal handlers and state."""
        self.context_manager = ContextManager()
        self._model_manager: Optional[LLMModelManager] = None
        self._model_manager_lock = threading.Lock()
        self._interrupted = False
        self._download_dialog_showing = False
        self._download_dialog = None
        self._pending_llm_request = (
            None  # Store pending request during download
        )
        self.manager_thread: Optional[QThread] = None
        self.download_manager = None
        super().__init__()
        self._llm_thread = None

        # Auto-unload timer state
        self._last_request_time: Optional[float] = None
        self._inactivity_timer: Optional[QTimer] = None
        self._inactivity_timeout = 300  # 5 minutes in seconds
        # DISABLED: QTimer cannot be used in worker threads - causes Qt crash
        # "QObject::killTimer: Timers cannot be stopped from another thread"
        self._auto_unload_enabled = (
            False  # Disabled to prevent Qt threading crash
        )

        # NOTE: Download completion is now handled via the queue mechanism
        # (WorkerManager.on_huggingface_download_complete adds to queue with
        # _message_type="download_complete") rather than direct signal registration.
        # This ensures download handling runs in the worker thread, not the main thread.

        # Auto-unload timer is DISABLED - QTimer cannot work in worker threads
        # self._start_inactivity_timer()

    @property
    def use_openrouter(self) -> bool:
        """Check if using OpenRouter model service.

        Returns:
            True if OpenRouter is configured
        """
        return (
            self.llm_generator_settings.model_service
            == ModelService.OPENROUTER.value
        )

    @property
    def use_ollama(self) -> bool:
        """Check if using Ollama model service.

        Returns:
            True if Ollama is configured
        """
        return (
            self.llm_generator_settings.model_service
            == ModelService.OLLAMA.value
        )

    @property
    def has_model_manager(self) -> bool:
        """Check if model manager exists without creating it.

        Returns:
            True if model manager is initialized
        """
        return self._model_manager is not None

    @property
    def model_manager(self) -> LLMModelManager:
        """Get the unified model manager for all backends.

        Returns:
            LLMModelManager instance
        """
        with self._model_manager_lock:
            if self._model_manager is None:
                self._model_manager = LLMModelManager()

                if self.use_openrouter:
                    self._model_manager.llm_settings.use_local_llm = False
                    self._model_manager.llm_settings.use_openrouter = True
                elif self.use_ollama:
                    self._model_manager.llm_settings.use_local_llm = False
                    self._model_manager.llm_settings.use_ollama = True
                else:
                    self._model_manager.llm_settings.use_local_llm = True

            return self._model_manager

    @property
    def local_model_manager(self) -> LLMModelManager:
        """Get model manager configured for local models.

        Returns:
            LLMModelManager configured for local execution
        """
        manager = LLMModelManager()
        manager.llm_settings.use_local_llm = True
        manager.llm_settings.use_openrouter = False
        manager.llm_settings.use_ollama = False
        return manager

    def on_conversation_deleted_signal(self, data: Dict) -> None:
        """Handle conversation deletion.

        Args:
            data: Signal data dictionary
        """
        self.model_manager.on_conversation_deleted(data)

    def on_section_changed_signal(self, data: Dict = None) -> None:
        """Handle section change in UI.
        
        Args:
            data: Optional signal data with section info
        """
        self.model_manager.on_section_changed()

    def on_llm_model_changed_signal(self, data: Dict) -> None:
        """Handle model change - unload without clearing manager reference.

        Args:
            data: Signal data dictionary
        """
        if self._model_manager:
            self._model_manager.unload()

    def on_rag_load_documents_signal(self, data: Dict) -> None:
        """Handle the signal to load documents into the RAG engine.

        Args:
            data: Dictionary containing documents and clear_documents flag
        """
        self.logger.debug("Worker received RAG signal!")

        # Access model_manager property which will create it if needed
        # This ensures the manager exists before we try to load documents
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
        """Clear all previous RAG documents."""
        if hasattr(self.model_manager, "clear_rag_documents"):
            self.model_manager.clear_rag_documents()

    def _load_documents_into_rag(self, documents: list) -> None:
        """Load documents into the RAG engine.

        Args:
            documents: List of documents to load
        """
        for doc in documents:
            # If the caller passed a file path, use the file loader which will
            # pick the proper reader (epub/pdf/html/md/etc.)
            try:
                if isinstance(doc, str) and os.path.exists(doc):
                    self.model_manager.load_file_into_rag(doc)
                    continue

                # If bytes were passed (e.g., uploaded file content), we need
                # to detect extension or default to .epub if provided as attr
                if isinstance(doc, (bytes, bytearray)):
                    # Fallback name and extension - caller could pass a tuple
                    # or dict with more info in the future if needed.
                    self.model_manager.load_bytes_into_rag(
                        doc, source_name="upload", file_ext=".epub"
                    )
                    continue

                # If dict-like with content and file_type, use that
                if isinstance(doc, dict) and "content" in doc:
                    file_type = doc.get("file_type", "")
                    content = doc.get("content")
                    if file_type.lower() in [".html", "html"]:
                        self.model_manager.load_file_into_rag(
                            content,
                            source_name=doc.get("source_name", "web_content"),
                        )
                    elif file_type.lower() in [".epub", "epub"]:
                        # content should be bytes for epub; try to coerce
                        content_bytes = (
                            content
                            if isinstance(content, (bytes, bytearray))
                            else (str(content).encode("utf-8"))
                        )
                        self.model_manager.load_bytes_into_rag(
                            content_bytes,
                            source_name=doc.get("source_name", "epub_upload"),
                            file_ext=".epub",
                        )
                    else:
                        # Fallback to treating as HTML text
                        self.model_manager.load_html_into_rag(
                            str(content),
                            source_name=doc.get("source_name", "web_content"),
                        )
                    continue

                # If plain string content (HTML) - heuristics: contains <html> or a lot of whitespace
                if isinstance(doc, str) and (
                    "<html" in doc.lower()
                    or "<body" in doc.lower()
                    or len(doc) > 100
                ):
                    self.model_manager.load_html_into_rag(doc)
                    continue

                # Unrecognized type - convert to string and insert as HTML fallback
                self.model_manager.load_html_into_rag(str(doc))
            except Exception as e:
                self.logger.error(
                    f"Failed to load RAG document {repr(doc)}: {e}"
                )

    def _start_inactivity_timer(self) -> None:
        """Start the inactivity monitoring timer."""
        if not self._auto_unload_enabled:
            return

        self._inactivity_timer = QTimer()
        self._inactivity_timer.timeout.connect(self._check_inactivity)
        # Check every 60 seconds
        self._inactivity_timer.start(60000)
        self.logger.info("LLM auto-unload timer started (5 minute timeout)")

    def _check_inactivity(self) -> None:
        """Check if model should be unloaded due to inactivity."""
        if not self._auto_unload_enabled or not self._last_request_time:
            return

        # Check if model is currently loaded
        if not self._model_manager or not self.has_model_manager:
            return

        from airunner.enums import ModelStatus, ModelType

        # Only unload if model is actually loaded
        if (
            self._model_manager.model_status.get(ModelType.LLM)
            != ModelStatus.LOADED
        ):
            return

        # Calculate time since last request
        inactive_time = time.time() - self._last_request_time

        if inactive_time >= self._inactivity_timeout:
            self.logger.info(
                f"LLM model idle for {int(inactive_time/60)} minutes - auto-unloading"
            )
            self.unload_llm()
            self._last_request_time = None  # Reset timestamp

    def _update_activity_timestamp(self) -> None:
        """Update the last request timestamp."""
        self._last_request_time = time.time()

    def on_quit_application_signal(self, data: Optional[Dict] = None) -> None:
        """Handle application quit signal.

        Args:
            data: Optional signal data dictionary
        """
        self.logger.debug("Quitting LLM")
        self.running = False
        if self._model_manager:
            self._model_manager.unload()
        if self._llm_thread is not None:
            self._llm_thread.join()

    def on_llm_on_unload_signal(self, data: Optional[Dict] = None) -> None:
        """Handle LLM unload signal.

        Args:
            data: Optional signal data dictionary
        """
        self.unload_llm(data)

    def unload_llm(self, data: Optional[Dict] = None) -> None:
        """Unload the LLM model and execute callback.

        Args:
            data: Optional dictionary with callback function
        """
        if not self._model_manager:
            return
        data = data or {}
        self._model_manager.unload()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_llm_load_model_signal(self, data: Dict) -> None:
        """Handle model load request.

        Args:
            data: Signal data dictionary
        """
        self._load_llm_thread(data)

    def on_llm_clear_history_signal(self, data: Optional[Dict] = None) -> None:
        """Handle clear history request.

        Args:
            data: Optional signal data dictionary
        """
        if self._model_manager:
            self._model_manager.clear_history(data)

    def on_llm_request_signal(self, message: dict) -> None:
        """Handle incoming LLM generation request.

        CRITICAL: Reset interrupt flag here so user can continue conversation
        after canceling. The interrupt flag is meant to skip the CURRENT
        interrupted message, not future messages.

        Args:
            message: Request message dictionary
        """
        self.logger.info(
            f"Received LLM request signal: {list(message.keys())}"
        )
        if self._interrupted:
            self.logger.info("Clearing interrupt flag - new message received")
            self._interrupted = False

        # Ensure every request has a request_id for streaming correlation
        request_id = message.get("request_id") or str(uuid.uuid4())
        message["request_id"] = request_id
        if isinstance(message.get("request_data"), dict):
            # Mirror into request_data so downstream consumers can access it
            message["request_data"].setdefault("request_id", request_id)
        self.logger.debug(f"Assigned request_id={request_id} to incoming request")

        # Track activity for auto-unload timer
        self._update_activity_timestamp()

        self.add_to_queue(message)
        self.logger.info(f"Added request to queue")

    def llm_on_interrupt_process_signal(self, data=None) -> None:
        """Handle interrupt signal - stop ongoing generation and clear queue.
        
        Args:
            data: Optional signal data (not used but required for signal handler signature)
        """
        self._interrupted = True
        self.clear_queue()
        self.logger.info("Interrupted and cleared LLM generation queue")

        if hasattr(self, "_model_manager") and self._model_manager is not None:
            self.logger.info(
                f"Calling do_interrupt on model_manager {id(self._model_manager)}"
            )
            try:
                self._model_manager.do_interrupt()
            except Exception as e:
                self.logger.error(
                    f"Error calling do_interrupt(): {e}", exc_info=True
                )
        else:
            self.logger.warning(f"Model manager not available for interrupt")

    def on_llm_add_chatbot_response_to_history(self, message: Dict) -> None:
        """Add chatbot response to conversation history.

        Args:
            message: Message dictionary to add
        """
        self.model_manager.add_chatbot_response_to_history(message)

    def on_llm_load_conversation(self, message: Dict) -> None:
        """Load a conversation into the model manager.

        Args:
            message: Conversation data dictionary
        """
        try:
            self.model_manager.load_conversation(message)
        except Exception as e:
            self.logger.error(f"Error in on_load_conversation: {e}")

    def start_worker_thread(self) -> None:
        """Start the worker thread if LLM is enabled."""
        if self.application_settings.llm_enabled or AIRUNNER_LLM_ON:
            self._load_llm_thread()

    def handle_message(self, message: Dict) -> None:
        """Process queued messages for LLM generation.

        The interrupt flag is NOT reset here - it's reset in on_llm_request_signal
        when a NEW message arrives. This ensures:
        1. Interrupted message is skipped
        2. Flag persists to prevent queue backup from processing
        3. Next user message clears the flag and processes normally

        Args:
            message: Message dictionary to process
        """
        # Handle download complete messages from the queue
        # This ensures download completion is processed in the worker thread,
        # not the main thread, preventing UI lockups during model loading
        if message.get("_message_type") == "download_complete":
            self.logger.info("Processing download complete message from queue")
            self.on_huggingface_download_complete_signal(message.get("data", {}))
            return

        if self._interrupted:
            self.logger.info("Skipping message - worker interrupted")
            return

        self.logger.info(
            f"handle_message called with keys: {list(message.keys())}"
        )
        self.logger.info(f"request_id in message: {message.get('request_id')}")

        # Store the request in case a download is triggered
        # This will be retried after download completes
        self._pending_llm_request = message
        self.logger.info(
            f"Stored pending request with ID: {message.get('request_id')}"
        )

        manager = self.model_manager

        # Check for RAG files in the request and load them if present
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

        result = manager.handle_request(
            message, self.context_manager.all_contexts()
        )

        # Clear pending request only if request truly completed successfully
        # Check for error responses (response starting with "Error:")
        if result:
            response_text = result.get("response", "")
            has_error = result.get("error") or (
                isinstance(response_text, str)
                and response_text.startswith("Error:")
            )

            if not has_error:
                self.logger.info(
                    "Request completed successfully, clearing pending request"
                )
                self._pending_llm_request = None
                
                # NOTE: We do NOT emit LLM_TEXT_STREAMED_SIGNAL here.
                # The generation_mixin already handles streaming tokens and sending
                # the end-of-message signal. Emitting here would cause duplicate
                # TTS generation (the full message would be spoken twice).
            else:
                self.logger.info(
                    f"Request failed with error, keeping pending request for retry after download"
                )

    def _load_llm_thread(self, data: Optional[Dict] = None) -> None:
        """Load LLM in a separate thread.

        Args:
            data: Optional load configuration
        """
        self._llm_thread = threading.Thread(
            target=self._load_llm, args=(data,)
        )
        self._llm_thread.start()

    def load(self) -> None:
        """Load the LLM model synchronously."""
        self._load_llm()

    def _load_llm(self, data: Optional[Dict] = None) -> None:
        """Internal method to load LLM and execute callback.

        Args:
            data: Optional dictionary with callback function
        """
        data = data or {}
        if self._model_manager is not None:
            self._model_manager.load()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def unload(self, data: Optional[Dict] = None) -> None:
        """Unload the LLM model and free VRAM/resources.

        This method is required for model load balancing.

        Args:
            data: Optional unload configuration
        """
        self.unload_llm(data)
