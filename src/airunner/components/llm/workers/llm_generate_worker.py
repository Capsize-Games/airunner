import threading
from typing import Dict, Optional, Type, List

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
from airunner.components.llm.data.fine_tuned_model import FineTunedModel
import uuid
import os

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
            SignalCode.RAG_INDEX_ALL_DOCUMENTS: self.on_rag_index_all_documents_signal,
            SignalCode.RAG_INDEX_SELECTED_DOCUMENTS: self.on_rag_index_selected_documents_signal,
            SignalCode.RAG_INDEX_CANCEL: self.on_rag_index_cancel_signal,
            SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL: self.on_llm_add_chatbot_response_to_history,
            SignalCode.LOAD_CONVERSATION: self.on_llm_load_conversation,
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.llm_on_interrupt_process_signal,
            SignalCode.QUIT_APPLICATION: self.on_quit_application_signal,
            SignalCode.CONVERSATION_DELETED: self.on_conversation_deleted_signal,
            SignalCode.SECTION_CHANGED: self.on_section_changed_signal,
            SignalCode.LLM_MODEL_CHANGED: self.on_llm_model_changed_signal,
            SignalCode.RAG_LOAD_DOCUMENTS: self.on_rag_load_documents_signal,
            SignalCode.INDEX_DOCUMENT: self.on_index_document_signal,
            SignalCode.LLM_START_FINE_TUNE: self.on_llm_start_fine_tune_signal,
            SignalCode.LLM_FINE_TUNE_CANCEL: self.on_llm_fine_tune_cancel_signal,
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

    def on_rag_index_all_documents_signal(self, data: Dict):
        """Handle manual document indexing request."""
        self.logger.info("Received RAG_INDEX_ALL_DOCUMENTS signal")

        # Run indexing in a separate thread to avoid blocking the worker's event loop
        indexing_thread = threading.Thread(
            target=self._index_all_documents_thread, args=(data,)
        )
        indexing_thread.start()

    def _index_all_documents_thread(self, data: Dict):
        """Run indexing in a separate thread to keep UI responsive."""
        # Ensure LLM is loaded - use same pattern as on_index_document_signal
        if not self.model_manager or not self.model_manager.agent:
            self.logger.info(
                "Model manager or agent not available, loading LLM for indexing..."
            )
            try:
                # Use load() method which synchronously loads the model
                self.load()
            except Exception as e:
                self.logger.error(f"Failed to load LLM for indexing: {e}")
                self.emit_signal(
                    SignalCode.RAG_INDEXING_COMPLETE,
                    {
                        "success": False,
                        "message": f"Failed to load LLM: {str(e)}",
                    },
                )
                return

        # Check again if agent is available after loading
        if not self.model_manager or not self.model_manager.agent:
            self.logger.error("Model manager loaded but agent is still None")
            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {
                    "success": False,
                    "message": "LLM agent not available after loading",
                },
            )
            return

        # Check if agent supports indexing
        if not hasattr(self.model_manager.agent, "index_all_documents"):
            self.logger.error("Agent does not support manual indexing")
            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {
                    "success": False,
                    "message": "Agent does not support indexing",
                },
            )
            return

        # Start indexing
        self.logger.info("Starting manual document indexing with loaded agent")
        try:
            self.model_manager.agent.index_all_documents()
        except Exception as e:
            self.logger.error(f"Error during indexing: {e}")
            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {
                    "success": False,
                    "message": f"Indexing error: {str(e)}",
                },
            )

    def on_rag_index_selected_documents_signal(self, data: Dict):
        """Handle selective document indexing request with file paths."""
        file_paths = data.get("file_paths", [])
        if not file_paths:
            self.logger.warning(
                "RAG_INDEX_SELECTED_DOCUMENTS called with no file paths"
            )
            return
        self.logger.info(
            f"Received RAG_INDEX_SELECTED_DOCUMENTS signal for {len(file_paths)} documents"
        )

        # Run indexing in a separate thread to avoid blocking the worker's event loop
        indexing_thread = threading.Thread(
            target=self._index_selected_documents_thread, args=(file_paths,)
        )
        indexing_thread.start()

    def on_llm_start_fine_tune_signal(self, data: Dict):
        """Start a fine-tune job in a separate thread."""
        files = data.get("files", [])
        model_name = data.get("model_name")

        def _run():
            try:
                # Emit initial progress
                self.emit_signal(
                    SignalCode.LLM_FINE_TUNE_PROGRESS,
                    {"progress": 0, "message": "Preparing..."},
                )

                # Prepare training examples by reading documents (DB first, then file)
                from typing import Tuple

                from airunner.components.llm.utils.document_extraction import (
                    extract_text,
                )

                def _read_document_content(path: str) -> Tuple[str, str]:
                    """Return (title, content) for a given path. Try DB first, then filesystem."""
                    title = os.path.basename(path)
                    content = ""
                    try:
                        db_docs = DBDocument.objects.filter_by(path=path)
                        if db_docs and len(db_docs) > 0:
                            db_doc = db_docs[0]
                            title = (
                                getattr(db_doc, "title", None)
                                or getattr(db_doc, "name", None)
                                or title
                            )
                            # try several possible content fields
                            content = (
                                getattr(db_doc, "text", None)
                                or getattr(db_doc, "content", None)
                                or getattr(db_doc, "value", None)
                            )
                    except Exception:
                        content = ""

                    if not content:
                        # Prefer smart extraction for common ebook/pdf types
                        try:
                            extracted = extract_text(path)
                            content = extracted or ""
                        except Exception:
                            content = ""

                    if content:
                        # basic normalization
                        content = " ".join(content.split())

                    return title or os.path.basename(path), content or ""

                def _chunk_text_to_examples(
                    title: str, text: str, max_chars: int = 2000
                ) -> List[tuple]:
                    examples: List[tuple] = []
                    if not text:
                        return examples
                    start = 0
                    idx = 1
                    length = len(text)
                    while start < length:
                        chunk = text[start : start + max_chars]
                        examples.append((f"{title} - part {idx}", chunk))
                        start += max_chars
                        idx += 1
                    return examples

                def _prepare_long_examples(
                    title: str, text: str
                ) -> List[tuple]:
                    # Long context: emit fewer, larger examples (attempt to keep as one per document)
                    if not text:
                        return []
                    # collapse whitespace and keep as single example if under limit
                    max_chars = 10000
                    if len(text) <= max_chars:
                        return [(title, text)]
                    # otherwise chunk into larger pieces
                    return _chunk_text_to_examples(
                        title, text, max_chars=max_chars
                    )

                def _prepare_author_style_examples(
                    title: str, text: str
                ) -> List[tuple]:
                    # Author-Style: try to create examples that preserve author voice by keeping
                    # paragraph boundaries and short chunks with metadata in the subject
                    if not text:
                        return []
                    paragraphs = [
                        p.strip() for p in text.split("\n\n") if p.strip()
                    ]
                    examples: List[tuple] = []
                    idx = 1
                    for p in paragraphs:
                        # keep paragraphs up to 2000 chars
                        if len(p) > 2000:
                            subchunks = _chunk_text_to_examples(
                                f"{title} - part {idx}", p, 2000
                            )
                            examples.extend(subchunks)
                            idx += len(subchunks)
                        else:
                            examples.append((f"{title} - para {idx}", p))
                            idx += 1
                    return examples

                fmt = data.get("format", "qa")

                # If user provided prepared examples via the signal payload (from preview), prefer them
                training_examples: List[tuple] = []
                provided = data.get("examples")
                if provided and isinstance(provided, (list, tuple)):
                    try:
                        # Expect list of (title, text) tuples
                        training_examples = [tuple(x) for x in provided]
                        self.emit_signal(
                            SignalCode.LLM_FINE_TUNE_PROGRESS,
                            {
                                "progress": 5,
                                "message": f"Using {len(training_examples)} user-selected examples",
                            },
                        )
                    except Exception:
                        training_examples = []
                else:
                    for path in files:
                        title, content = _read_document_content(path)
                        if not content:
                            self.logger.warning(
                                f"No content found for training file: {path}"
                            )
                            continue
                        if fmt == "long":
                            chunks = _prepare_long_examples(title, content)
                        elif fmt == "author":
                            chunks = _prepare_author_style_examples(
                                title, content
                            )
                        else:
                            # default to qa pairs chunking
                            chunks = _chunk_text_to_examples(title, content)
                        training_examples.extend(chunks)

                if not training_examples:
                    self.logger.error(
                        "No training examples prepared; aborting fine-tune"
                    )
                    self.emit_signal(
                        SignalCode.LLM_FINE_TUNE_COMPLETE,
                        {
                            "success": False,
                            "model_name": model_name,
                            "message": "No training data",
                        },
                    )
                    return

                # Emit progress after preparing examples
                self.emit_signal(
                    SignalCode.LLM_FINE_TUNE_PROGRESS,
                    {
                        "progress": 5,
                        "message": f"Prepared {len(training_examples)} training examples",
                    },
                )

                # Ensure tokenizer and base model are loaded for training.
                # Important: do NOT load the full agent here (which initializes RAG
                # and embeddings like sentence-transformers e5-large) because that
                # can consume significant GPU memory and is unnecessary for fine-tune.
                if not self.model_manager:
                    # Create a local model manager instance but DO NOT call
                    # model_manager.load() because that would initialize the
                    # agent and RAG (which in turn loads sentence-transformers
                    # e5-large embeddings). Instead instantiate the manager
                    # and load tokenizer+model only.
                    try:
                        self._model_manager = self.local_model_manager
                    except Exception:
                        self.logger.exception(
                            "Failed to obtain local model manager"
                        )
                        self.emit_signal(
                            SignalCode.LLM_FINE_TUNE_COMPLETE,
                            {
                                "success": False,
                                "model_name": model_name,
                                "message": "Failed to obtain model manager",
                            },
                        )
                        return

                try:
                    # Mark finetune-only mode to prevent loading the agent/RAG/embeddings
                    try:
                        self.model_manager._skip_agent_load = True
                    except Exception:
                        pass

                    # Load only tokenizer and the base model. Avoid calling
                    # model_manager.load() which also loads the agent/embeddings.
                    self.model_manager._load_tokenizer()
                    self.model_manager._load_model()
                except Exception as e:
                    self.logger.error(
                        f"Failed to load tokenizer/model before training: {e}"
                    )
                    self.emit_signal(
                        SignalCode.LLM_FINE_TUNE_COMPLETE,
                        {
                            "success": False,
                            "model_name": model_name,
                            "message": f"Failed to load model: {e}",
                        },
                    )
                    return
                finally:
                    # Ensure the flag is cleared; training path itself may set it
                    try:
                        self.model_manager._skip_agent_load = False
                    except Exception:
                        pass

                # If the model manager has a train method (from TrainingMixin), call it with prepared examples
                if hasattr(self.model_manager, "train"):
                    try:

                        def _progress_cb(data: dict):
                            # Ensure keys are serializable/simple
                            progress = data.get("progress")
                            step = data.get("step")
                            payload = {"progress": progress, "step": step}
                            self.emit_signal(
                                SignalCode.LLM_FINE_TUNE_PROGRESS, payload
                            )

                        self.model_manager.train(
                            training_data=training_examples,
                            username="User",
                            botname="Assistant",
                            progress_callback=_progress_cb,
                        )
                    except Exception as e:
                        self.logger.error(f"Fine-tune failed: {e}")
                        self.emit_signal(
                            SignalCode.LLM_FINE_TUNE_COMPLETE,
                            {
                                "success": False,
                                "model_name": model_name,
                                "message": str(e),
                            },
                        )
                        return

                # On success: save a DB record and notify UI
                try:
                    FineTunedModel.create_record(
                        name=model_name or "",
                        files=files,
                        settings={},
                    )
                except Exception:
                    self.logger.exception(
                        "Failed to record fine-tuned model in DB"
                    )

                self.emit_signal(
                    SignalCode.LLM_FINE_TUNE_PROGRESS,
                    {"progress": 100, "message": "Saving model..."},
                )
                self.emit_signal(
                    SignalCode.LLM_FINE_TUNE_COMPLETE,
                    {"success": True, "model_name": model_name},
                )
            except Exception as e:
                self.logger.error(f"Exception in fine-tune thread: {e}")
                self.emit_signal(
                    SignalCode.LLM_FINE_TUNE_COMPLETE,
                    {
                        "success": False,
                        "model_name": model_name,
                        "message": str(e),
                    },
                )

        t = threading.Thread(target=_run)
        t.start()

    def on_llm_fine_tune_cancel_signal(self, data: Dict = None):
        """Handle cancel request. Currently tries to interrupt the model manager."""
        # Attempt to call model_manager.do_interrupt() to stop training
        try:
            if self.model_manager:
                self.model_manager.cancel_fine_tune()
        except Exception:
            self.logger.exception("Error while attempting to cancel fine-tune")
        # Notify UI
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_CANCEL, {"message": "Cancelled by user"}
        )

    def _index_selected_documents_thread(self, file_paths: list):
        """Run selective indexing in a separate thread to keep UI responsive."""
        # Ensure LLM is loaded
        if not self.model_manager or not self.model_manager.agent:
            self.logger.info(
                "Model manager or agent not available, loading LLM for indexing..."
            )
            try:
                self.load()
            except Exception as e:
                self.logger.error(f"Failed to load LLM for indexing: {e}")
                self.emit_signal(
                    SignalCode.RAG_INDEXING_COMPLETE,
                    {
                        "success": False,
                        "message": f"Failed to load LLM: {str(e)}",
                    },
                )
                return

        # Check again if agent is available after loading
        if not self.model_manager or not self.model_manager.agent:
            self.logger.error("Model manager loaded but agent is still None")
            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {
                    "success": False,
                    "message": "LLM agent not available after loading",
                },
            )
            return

        # Check if agent supports indexing
        if not hasattr(self.model_manager.agent, "_index_single_document"):
            self.logger.error("Agent does not support document indexing")
            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {
                    "success": False,
                    "message": "Agent does not support indexing",
                },
            )
            return

        # Index each document
        total = len(file_paths)
        for idx, file_path in enumerate(file_paths):
            try:
                # Get document from database
                db_docs = DBDocument.objects.filter_by(path=file_path)
                if not db_docs or len(db_docs) == 0:
                    self.logger.warning(
                        f"Document not found in database: {file_path}"
                    )
                    self.emit_signal(
                        SignalCode.DOCUMENT_INDEX_FAILED,
                        {
                            "path": file_path,
                            "error": "Document not found in database",
                        },
                    )
                    continue

                db_doc = db_docs[0]

                # Emit progress
                self.emit_signal(
                    SignalCode.RAG_INDEXING_PROGRESS,
                    {
                        "current": idx,
                        "total": total,
                        "progress": int((idx / total) * 100),
                    },
                )

                # Index the document
                self.logger.info(
                    f"Indexing document {idx + 1}/{total}: {file_path}"
                )
                success = self.model_manager.agent._index_single_document(
                    db_doc
                )

                if success:
                    DBDocument.objects.update(pk=db_doc.id, active=True)
                    self.emit_signal(
                        SignalCode.DOCUMENT_INDEXED, {"path": file_path}
                    )
                else:
                    self.emit_signal(
                        SignalCode.DOCUMENT_INDEX_FAILED,
                        {
                            "path": file_path,
                            "error": "No content could be extracted",
                        },
                    )

            except Exception as e:
                self.logger.error(f"Failed to index {file_path}: {e}")
                self.emit_signal(
                    SignalCode.DOCUMENT_INDEX_FAILED,
                    {"path": file_path, "error": str(e)},
                )

        # Emit completion
        self.emit_signal(
            SignalCode.RAG_INDEXING_COMPLETE,
            {"success": True, "message": f"Indexed {total} documents"},
        )

    def on_rag_index_cancel_signal(self, data: Dict):
        """Handle cancel indexing request by setting interrupt flags if available."""
        try:
            # Prefer higher-level manager interrupt if available
            if self.model_manager and hasattr(
                self.model_manager, "do_interrupt"
            ):
                try:
                    self.model_manager.do_interrupt()
                    self.logger.info("Called model_manager.do_interrupt()")
                    return
                except Exception:
                    pass

            # Fallback: set agent flag
            if (
                self.model_manager
                and self.model_manager.agent
                and hasattr(self.model_manager.agent, "do_interrupt")
            ):
                setattr(self.model_manager.agent, "do_interrupt", True)
                self.logger.info("Set agent.do_interrupt = True")
        except Exception as e:
            self.logger.error(f"Error during cancel indexing: {e}")

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
            self.logger.warning(
                "INDEX_DOCUMENT signal received with invalid path"
            )
            return

        import os

        filename = os.path.basename(document_path)
        self.logger.info(f"Starting indexing process for: {filename}")

        # Get the document from database first
        db_docs = DBDocument.objects.filter_by(path=document_path)
        if not db_docs or len(db_docs) == 0:
            self.logger.error(f"Document not found in database: {filename}")
            self.emit_signal(
                SignalCode.DOCUMENT_INDEX_FAILED,
                {
                    "path": document_path,
                    "error": "Document not found in database",
                },
            )
            return

        db_doc = db_docs[0]

        if not self.model_manager or not self.model_manager.agent:
            self.logger.info("Loading LLM model for indexing...")
            self.load()
        if not self.model_manager or not self.model_manager.agent:
            self.logger.error(
                f"Failed to load LLM model, cannot index: {filename}"
            )
            self.emit_signal(
                SignalCode.DOCUMENT_INDEX_FAILED,
                {"path": document_path, "error": "Failed to load LLM model"},
            )
            return

        try:
            agent = self.model_manager.agent

            self.logger.info(f"Indexing document: {filename}")
            # Use the proper indexing method
            success = agent._index_single_document(db_doc)

            if success:
                # Mark as active in database
                DBDocument.objects.update(pk=db_doc.id, active=True)
                self.logger.info(f"Successfully indexed document: {filename}")

                # Emit success signal
                self.emit_signal(
                    SignalCode.DOCUMENT_INDEXED, {"path": document_path}
                )
            else:
                self.logger.error(f"Failed to index document: {filename}")
                self.emit_signal(
                    SignalCode.DOCUMENT_INDEX_FAILED,
                    {
                        "path": document_path,
                        "error": "No content could be extracted from document. The file may be corrupted, empty, or in an unsupported format.",
                    },
                )

        except Exception as e:
            self.logger.error(
                f"Failed to index document {filename}: {str(e)}", exc_info=True
            )
            # Emit failure signal so UI can handle it
            self.emit_signal(
                SignalCode.DOCUMENT_INDEX_FAILED,
                {"path": document_path, "error": str(e)},
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
