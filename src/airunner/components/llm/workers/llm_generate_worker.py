"""LLM generation worker with signal-based coordination."""

import threading
from typing import Dict, Optional

from PySide6.QtCore import QThread

from airunner.enums import ModelService
from airunner.components.application.workers.worker import Worker
from airunner.settings import AIRUNNER_LLM_ON
from airunner.components.llm.managers.llm_model_manager import LLMModelManager
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
        self.manager_thread: Optional[QThread] = None
        self.download_manager = None
        super().__init__()
        self._llm_thread = None

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

    def on_section_changed_signal(self) -> None:
        """Handle section change in UI."""
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
        if not self.has_model_manager or not self.model_manager.agent:
            return

        if data.get("clear_documents", False):
            self._clear_rag_documents()

        documents = data.get("documents", [])
        if documents:
            self._load_documents_into_rag(documents)

    def _clear_rag_documents(self) -> None:
        """Clear all previous RAG documents."""
        if hasattr(self.model_manager.agent, "clear_rag_documents"):
            self.model_manager.agent.clear_rag_documents()

    def _load_documents_into_rag(self, documents: list) -> None:
        """Load documents into the RAG engine.

        Args:
            documents: List of documents to load
        """
        for doc in documents:
            self.model_manager.agent.load_html_into_rag(doc)

    def on_quit_application_signal(self) -> None:
        """Handle application quit signal."""
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
            f"[LLM WORKER] Received LLM request signal: {list(message.keys())}"
        )
        if self._interrupted:
            self.logger.info("Clearing interrupt flag - new message received")
            self._interrupted = False

        self.add_to_queue(message)
        self.logger.info(f"[LLM WORKER] Added request to queue")

    def llm_on_interrupt_process_signal(self) -> None:
        """Handle interrupt signal - stop ongoing generation and clear queue."""
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
        if self._interrupted:
            self.logger.info("Skipping message - worker interrupted")
            return

        print(
            f"[LLM WORKER] handle_message called with keys: {list(message.keys())}",
            flush=True,
        )
        print(
            f"[LLM WORKER] request_id in message: {message.get('request_id')}",
            flush=True,
        )

        manager = self.model_manager
        manager.handle_request(message, self.context_manager.all_contexts())

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
