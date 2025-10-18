import os
import threading
from typing import Dict, Optional, Type, List, Tuple

from airunner.enums import SignalCode, ModelService
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
from airunner.components.llm.utils.document_extraction import extract_text


class LLMGenerateWorker(Worker):
    def __init__(self, local_agent_class=None):
        self.local_agent_class = local_agent_class
        self.signal_handlers = self._create_signal_handlers()
        self.context_manager = ContextManager()
        self._openrouter_model_manager: Optional[OpenRouterModelManager] = None
        self._ollama_model_manager: Optional[OllamaModelManager] = None
        self._local_model_manager: Optional[LLMModelManager] = None
        self._model_manager: Optional[Type[LLMModelManager]] = None
        super().__init__()
        self._llm_thread = None

    def _create_signal_handlers(self) -> Dict:
        """Create the signal handlers mapping."""
        return {
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

    @property
    def model_manager(self) -> Type[LLMModelManager]:
        if self._model_manager is None:
            self._model_manager = self._select_model_manager()
        return self._model_manager

    def _select_model_manager(self) -> Type[LLMModelManager]:
        """Select the appropriate model manager based on settings."""
        if self.use_openrouter:
            return self.openrouter_model_manager
        elif self.use_ollama:
            return self.ollama_model_manager
        else:
            return self.local_model_manager

    def on_conversation_deleted_signal(self, data):
        self.model_manager.on_conversation_deleted(data)

    def on_section_changed_signal(self):
        self.model_manager.on_section_changed()

    def on_llm_model_changed_signal(self, data: Dict):
        # Reset the model manager to ensure it's re-evaluated on next access
        self._model_manager = None
        self.unload_llm()

    def on_rag_load_documents_signal(self, data: Dict):
        """Handle the signal to load documents into the RAG engine."""
        if not self.model_manager or not self.model_manager.agent:
            return

        if data.get("clear_documents", False):
            self._clear_rag_documents()

        documents = data.get("documents", [])
        if documents:
            self._load_documents_into_rag(documents)

    def _clear_rag_documents(self):
        """Clear all previous RAG documents."""
        if hasattr(self.model_manager.agent, "clear_rag_documents"):
            self.model_manager.agent.clear_rag_documents()

    def _load_documents_into_rag(self, documents: List):
        """Load documents into the RAG engine."""
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
        indexing_thread = threading.Thread(
            target=self._index_all_documents_thread, args=(data,)
        )
        indexing_thread.start()

    def _index_all_documents_thread(self, data: Dict):
        """Run indexing in a separate thread to keep UI responsive."""
        if not self._ensure_agent_loaded("indexing"):
            return

        if not self._validate_agent_supports_indexing():
            return

        self._perform_all_documents_indexing()

    def _ensure_agent_loaded(self, operation: str) -> bool:
        """Ensure the agent is loaded for the specified operation."""
        if self.model_manager and self.model_manager.agent:
            return True

        self.logger.info(f"Loading LLM for {operation}...")
        try:
            self.load()
        except Exception as e:
            self.logger.error(f"Failed to load LLM for {operation}: {e}")
            self._emit_indexing_error(f"Failed to load LLM: {str(e)}")
            return False

        if not self.model_manager or not self.model_manager.agent:
            self.logger.error("Model manager loaded but agent is still None")
            self._emit_indexing_error("LLM agent not available after loading")
            return False

        return True

    def _validate_agent_supports_indexing(self) -> bool:
        """Validate that the agent supports indexing operations."""
        if not hasattr(self.model_manager.agent, "index_all_documents"):
            self.logger.error("Agent does not support manual indexing")
            self._emit_indexing_error("Agent does not support indexing")
            return False
        return True

    def _perform_all_documents_indexing(self):
        """Perform the actual indexing of all documents."""
        self.logger.info("Starting manual document indexing with loaded agent")
        try:
            self.model_manager.agent.index_all_documents()
        except Exception as e:
            self.logger.error(f"Error during indexing: {e}")
            self._emit_indexing_error(f"Indexing error: {str(e)}")

    def _emit_indexing_error(self, message: str):
        """Emit an indexing error signal."""
        self.emit_signal(
            SignalCode.RAG_INDEXING_COMPLETE,
            {"success": False, "message": message},
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
        t = threading.Thread(target=self._run_fine_tune, args=(data,))
        t.start()

    def _run_fine_tune(self, data: Dict):
        """Execute the fine-tuning process."""
        files = data.get("files", [])
        model_name = data.get("model_name")

        try:
            self.emit_signal(
                SignalCode.LLM_FINE_TUNE_PROGRESS,
                {"progress": 0, "message": "Preparing..."},
            )

            training_examples = self._prepare_training_examples(data, files)
            if not training_examples:
                self._emit_fine_tune_error(model_name, "No training data")
                return

            self._emit_training_progress(len(training_examples))

            if not self._setup_model_for_training(model_name):
                return

            if not self._execute_training(training_examples, model_name):
                return

            self._save_fine_tuned_model(model_name, files)
            self._emit_fine_tune_complete(model_name)

        except Exception as e:
            self.logger.error(f"Exception in fine-tune thread: {e}")
            self._emit_fine_tune_error(model_name, str(e))

    def _prepare_training_examples(
        self, data: Dict, files: List[str]
    ) -> List[Tuple]:
        """Prepare training examples from files or provided examples."""
        provided = data.get("examples")
        if provided and isinstance(provided, (list, tuple)):
            return self._use_provided_examples(provided)

        return self._extract_examples_from_files(
            files, data.get("format", "qa")
        )

    def _use_provided_examples(self, provided: List) -> List[Tuple]:
        """Use pre-selected examples from the UI."""
        try:
            training_examples = [tuple(x) for x in provided]
            self.emit_signal(
                SignalCode.LLM_FINE_TUNE_PROGRESS,
                {
                    "progress": 5,
                    "message": f"Using {len(training_examples)} user-selected examples",
                },
            )
            return training_examples
        except Exception:
            return []

    def _extract_examples_from_files(
        self, files: List[str], fmt: str
    ) -> List[Tuple]:
        """Extract training examples from files."""
        training_examples = []
        for path in files:
            title, content = self._read_document_content(path)
            if not content:
                self.logger.warning(
                    f"No content found for training file: {path}"
                )
                continue

            chunks = self._format_examples(title, content, fmt)
            training_examples.extend(chunks)

        return training_examples

    def _read_document_content(self, path: str) -> Tuple[str, str]:
        """Return (title, content) for a given path. Try DB first, then filesystem."""
        title, content = self._try_db_content(path)

        if not content:
            content = self._try_file_extraction(path)

        if content:
            content = " ".join(content.split())

        return title, content or ""

    def _try_db_content(self, path: str) -> Tuple[str, str]:
        """Try to get content from database."""
        title = os.path.basename(path)
        try:
            db_docs = DBDocument.objects.filter_by(path=path)
            if db_docs and len(db_docs) > 0:
                db_doc = db_docs[0]
                title = (
                    getattr(db_doc, "title", None)
                    or getattr(db_doc, "name", None)
                    or title
                )
                content = (
                    getattr(db_doc, "text", None)
                    or getattr(db_doc, "content", None)
                    or getattr(db_doc, "value", None)
                )
                return title, content or ""
        except Exception:
            pass
        return title, ""

    def _try_file_extraction(self, path: str) -> str:
        """Try to extract content from file."""
        try:
            extracted = extract_text(path)
            return extracted or ""
        except Exception:
            return ""

    def _format_examples(self, title: str, text: str, fmt: str) -> List[Tuple]:
        """Format text into training examples based on format type."""
        if fmt == "long":
            return self._prepare_long_examples(title, text)
        elif fmt == "author":
            return self._prepare_author_style_examples(title, text)
        else:
            return self._chunk_text_to_examples(title, text)

    def _chunk_text_to_examples(
        self, title: str, text: str, max_chars: int = 2000
    ) -> List[Tuple]:
        """Chunk text into training examples."""
        examples = []
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

    def _prepare_long_examples(self, title: str, text: str) -> List[Tuple]:
        """Prepare long-context examples (fewer, larger chunks)."""
        if not text:
            return []
        max_chars = 10000
        if len(text) <= max_chars:
            return [(title, text)]
        return self._chunk_text_to_examples(title, text, max_chars=max_chars)

    def _prepare_author_style_examples(
        self, title: str, text: str
    ) -> List[Tuple]:
        """Prepare author-style examples preserving paragraph boundaries."""
        if not text:
            return []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        examples = []
        idx = 1
        for p in paragraphs:
            if len(p) > 2000:
                subchunks = self._chunk_text_to_examples(
                    f"{title} - part {idx}", p, 2000
                )
                examples.extend(subchunks)
                idx += len(subchunks)
            else:
                examples.append((f"{title} - para {idx}", p))
                idx += 1
        return examples

    def _emit_training_progress(self, count: int):
        """Emit progress signal after preparing training examples."""
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_PROGRESS,
            {"progress": 5, "message": f"Prepared {count} training examples"},
        )

    def _setup_model_for_training(self, model_name: str) -> bool:
        """Set up model manager for training."""
        if not self.model_manager:
            if not self._initialize_model_manager(model_name):
                return False

        return self._load_model_for_training(model_name)

    def _initialize_model_manager(self, model_name: str) -> bool:
        """Initialize local model manager."""
        try:
            self._model_manager = self.local_model_manager
            return True
        except Exception:
            self.logger.exception("Failed to obtain local model manager")
            self._emit_fine_tune_error(
                model_name, "Failed to obtain model manager"
            )
            return False

    def _load_model_for_training(self, model_name: str) -> bool:
        """Load tokenizer and model without agent/RAG."""
        try:
            self.model_manager._skip_agent_load = True
        except Exception:
            pass

        try:
            self.model_manager._load_tokenizer()
            self.model_manager._load_model()
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to load tokenizer/model before training: {e}"
            )
            self._emit_fine_tune_error(
                model_name, f"Failed to load model: {e}"
            )
            return False
        finally:
            try:
                self.model_manager._skip_agent_load = False
            except Exception:
                pass

    def _execute_training(
        self, training_examples: List[Tuple], model_name: str
    ) -> bool:
        """Execute the training process."""
        if not hasattr(self.model_manager, "train"):
            return False

        try:
            self.model_manager.train(
                training_data=training_examples,
                username="User",
                botname="Assistant",
                progress_callback=self._training_progress_callback,
            )
            return True
        except Exception as e:
            self.logger.error(f"Fine-tune failed: {e}")
            self._emit_fine_tune_error(model_name, str(e))
            return False

    def _training_progress_callback(self, data: dict):
        """Callback for training progress updates."""
        progress = data.get("progress")
        step = data.get("step")
        payload = {"progress": progress, "step": step}
        self.emit_signal(SignalCode.LLM_FINE_TUNE_PROGRESS, payload)

    def _save_fine_tuned_model(self, model_name: str, files: List[str]):
        """Save fine-tuned model record to database."""
        try:
            FineTunedModel.create_record(
                name=model_name or "",
                files=files,
                settings={},
            )
        except Exception:
            self.logger.exception("Failed to record fine-tuned model in DB")

    def _emit_fine_tune_complete(self, model_name: str):
        """Emit completion signals."""
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_PROGRESS,
            {"progress": 100, "message": "Saving model..."},
        )
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_COMPLETE,
            {"success": True, "model_name": model_name},
        )

    def _emit_fine_tune_error(self, model_name: str, message: str):
        """Emit error signal for fine-tune failures."""
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_COMPLETE,
            {"success": False, "model_name": model_name, "message": message},
        )

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
        if not self._ensure_agent_loaded():
            return

        if not self._validate_indexing_support():
            return

        self._index_documents(file_paths)

    def _ensure_agent_loaded(self) -> bool:
        """Ensure model manager and agent are loaded."""
        if self.model_manager and self.model_manager.agent:
            return True

        self.logger.info(
            "Model manager or agent not available, loading LLM for indexing..."
        )
        try:
            self.load()
        except Exception as e:
            self.logger.error(f"Failed to load LLM for indexing: {e}")
            self._emit_indexing_error(f"Failed to load LLM: {str(e)}")
            return False

        if not self.model_manager or not self.model_manager.agent:
            self.logger.error("Model manager loaded but agent is still None")
            self._emit_indexing_error("LLM agent not available after loading")
            return False

        return True

    def _validate_indexing_support(self) -> bool:
        """Check if agent supports indexing."""
        if not hasattr(self.model_manager.agent, "_index_single_document"):
            self.logger.error("Agent does not support document indexing")
            self._emit_indexing_error("Agent does not support indexing")
            return False
        return True

    def _index_documents(self, file_paths: list):
        """Index each document in the list."""
        total = len(file_paths)
        for idx, file_path in enumerate(file_paths):
            self._emit_indexing_progress(idx, total)
            self._index_single_file(file_path, idx, total)

        self.emit_signal(
            SignalCode.RAG_INDEXING_COMPLETE,
            {"success": True, "message": f"Indexed {total} documents"},
        )

    def _emit_indexing_progress(self, idx: int, total: int):
        """Emit indexing progress signal."""
        self.emit_signal(
            SignalCode.RAG_INDEXING_PROGRESS,
            {
                "current": idx,
                "total": total,
                "progress": int((idx / total) * 100),
            },
        )

    def _index_single_file(self, file_path: str, idx: int, total: int):
        """Index a single document file."""
        try:
            db_doc = self._get_document_from_db(file_path)
            if not db_doc:
                return

            self.logger.info(
                f"Indexing document {idx + 1}/{total}: {file_path}"
            )
            success = self.model_manager.agent._index_single_document(db_doc)

            if success:
                DBDocument.objects.update(pk=db_doc.id, active=True)
                self.emit_signal(
                    SignalCode.DOCUMENT_INDEXED, {"path": file_path}
                )
            else:
                self._emit_index_failed(
                    file_path, "No content could be extracted"
                )

        except Exception as e:
            self.logger.error(f"Failed to index {file_path}: {e}")
            self._emit_index_failed(file_path, str(e))

    def _get_document_from_db(self, file_path: str):
        """Get document from database."""
        db_docs = DBDocument.objects.filter_by(path=file_path)
        if not db_docs or len(db_docs) == 0:
            self.logger.warning(f"Document not found in database: {file_path}")
            self._emit_index_failed(
                file_path, "Document not found in database"
            )
            return None
        return db_docs[0]

    def _emit_indexing_error(self, message: str):
        """Emit indexing error signal."""
        self.emit_signal(
            SignalCode.RAG_INDEXING_COMPLETE,
            {"success": False, "message": message},
        )

    def _emit_index_failed(self, path: str, error: str):
        """Emit document index failed signal."""
        self.emit_signal(
            SignalCode.DOCUMENT_INDEX_FAILED,
            {"path": path, "error": error},
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
        """Handle INDEX_DOCUMENT signal: index file, save index, update DB."""
        document_path = data.get("path", None)
        if not self._validate_document_path(document_path):
            return

        filename = os.path.basename(document_path)
        self.logger.info(f"Starting indexing process for: {filename}")

        db_doc = self._get_document_from_db(document_path)
        if not db_doc:
            return

        if not self._ensure_agent_loaded():
            self._emit_index_failed(document_path, "Failed to load LLM model")
            return

        self._process_document_indexing(document_path, db_doc, filename)

    def _validate_document_path(self, path) -> bool:
        """Validate document path from signal."""
        if not isinstance(path, str) or not path:
            self.logger.warning(
                "INDEX_DOCUMENT signal received with invalid path"
            )
            return False
        return True

    def _process_document_indexing(self, path: str, db_doc, filename: str):
        """Process single document indexing."""
        try:
            self.logger.info(f"Indexing document: {filename}")
            success = self.model_manager.agent._index_single_document(db_doc)

            if success:
                self._handle_indexing_success(path, db_doc, filename)
            else:
                self._handle_indexing_failure(path, filename)

        except Exception as e:
            self.logger.error(
                f"Failed to index document {filename}: {str(e)}", exc_info=True
            )
            self._emit_index_failed(path, str(e))

    def _handle_indexing_success(self, path: str, db_doc, filename: str):
        """Handle successful document indexing."""
        DBDocument.objects.update(pk=db_doc.id, active=True)
        self.logger.info(f"Successfully indexed document: {filename}")
        self.emit_signal(SignalCode.DOCUMENT_INDEXED, {"path": path})

    def _handle_indexing_failure(self, path: str, filename: str):
        """Handle failed document indexing."""
        self.logger.error(f"Failed to index document: {filename}")
        self._emit_index_failed(
            path,
            "No content could be extracted from document. "
            "The file may be corrupted, empty, or in an unsupported format.",
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
