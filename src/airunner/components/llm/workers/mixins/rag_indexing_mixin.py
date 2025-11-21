"""RAG and document indexing operations for LLM worker."""

import os
import threading
from typing import Dict, List

from airunner.enums import SignalCode
from airunner.components.documents.data.models.document import (
    Document as DBDocument,
)


class RAGIndexingMixin:
    """Handles RAG engine and document indexing operations.

    This mixin provides functionality for:
    - Reloading RAG indices
    - Indexing all documents
    - Indexing selected documents
    - Indexing single documents
    - Managing indexing progress and errors
    """

    def on_llm_reload_rag_index_signal(self) -> None:
        """Reload the RAG engine index."""
        if self._model_manager:
            self._model_manager.reload_rag_engine()

    def on_rag_index_all_documents_signal(self, data: Dict) -> None:
        """Handle manual document indexing request.

        Args:
            data: Signal data dictionary
        """
        self.logger.info("Received RAG_INDEX_ALL_DOCUMENTS signal")
        indexing_thread = threading.Thread(
            target=self._index_all_documents_thread, args=(data,)
        )
        indexing_thread.start()

    def _index_all_documents_thread(self, data: Dict) -> None:
        """Run indexing in a separate thread to keep UI responsive.

        Args:
            data: Signal data dictionary
        """
        if not self._ensure_agent_loaded("indexing"):
            return

        if not self._validate_agent_supports_indexing():
            return

        self._perform_all_documents_indexing()

    def _ensure_agent_loaded(self, operation: str = "operation") -> bool:
        """Ensure the agent is loaded for the specified operation.

        Args:
            operation: Name of operation requiring agent

        Returns:
            True if agent is loaded and available
        """
        # Accept either an explicit agent bound to the manager or the manager
        # performing the agent role itself (backwards compatibility).
        if self.model_manager and (
            getattr(self.model_manager, "agent", None)
            or hasattr(self.model_manager, "index_all_documents")
        ):
            return True

        self.logger.info(f"Loading LLM for {operation}...")
        try:
            self.load()
        except Exception as e:
            self.logger.error(f"Failed to load LLM for {operation}: {e}")
            self._emit_indexing_error(f"Failed to load LLM: {str(e)}")
            return False

        if not self.model_manager or (
            not getattr(self.model_manager, "agent", None)
            and not hasattr(self.model_manager, "index_all_documents")
        ):
            self.logger.error("Model manager loaded but agent is still None")
            self._emit_indexing_error("LLM agent not available after loading")
            return False

        return True

    def _validate_agent_supports_indexing(self) -> bool:
        """Validate that the agent supports indexing operations.

        Returns:
            True if agent supports indexing
        """
        # Support either an explicit agent or the model manager
        agent = (
            getattr(self.model_manager, "agent", None) or self.model_manager
        )
        if not hasattr(agent, "index_all_documents"):
            self.logger.error("Agent/manager does not support manual indexing")
            self._emit_indexing_error("Agent does not support indexing")
            return False
        return True

    def _perform_all_documents_indexing(self) -> None:
        """Perform the actual indexing of all documents."""
        self.logger.info("Starting manual document indexing with loaded agent")
        try:
            agent = (
                getattr(self.model_manager, "agent", None)
                or self.model_manager
            )
            agent.index_all_documents()
        except Exception as e:
            self.logger.error(f"Error during indexing: {e}")
            self._emit_indexing_error(f"Indexing error: {str(e)}")

    def _emit_indexing_error(self, message: str) -> None:
        """Emit an indexing error signal.

        Args:
            message: Error message to include
        """
        self.emit_signal(
            SignalCode.RAG_INDEXING_COMPLETE,
            {"success": False, "message": message},
        )

    def on_rag_index_selected_documents_signal(self, data: Dict) -> None:
        """Handle selective document indexing request with file paths.

        Args:
            data: Dictionary containing file_paths list
        """
        file_paths = data.get("file_paths", [])
        if not file_paths:
            self.logger.warning(
                "RAG_INDEX_SELECTED_DOCUMENTS called with no file paths"
            )
            return
        self.logger.info(
            f"Received RAG_INDEX_SELECTED_DOCUMENTS signal for {len(file_paths)} documents"
        )

        indexing_thread = threading.Thread(
            target=self._index_selected_documents_thread, args=(file_paths,)
        )
        indexing_thread.start()

    def _index_selected_documents_thread(self, file_paths: List[str]) -> None:
        """Run selective indexing in a separate thread to keep UI responsive.

        Args:
            file_paths: List of file paths to index
        """
        if not self._ensure_agent_loaded():
            return

        if not self._validate_indexing_support():
            return

        self._index_documents(file_paths)

    def _validate_indexing_support(self) -> bool:
        """Check if agent supports indexing.

        Returns:
            True if agent supports document indexing
        """
        agent = (
            getattr(self.model_manager, "agent", None) or self.model_manager
        )
        if not hasattr(agent, "_index_single_document"):
            self.logger.error(
                "Agent/manager does not support document indexing"
            )
            self._emit_indexing_error("Agent does not support indexing")
            return False
        return True

    def _index_documents(self, file_paths: List[str]) -> None:
        """Index each document in the list.

        Args:
            file_paths: List of file paths to index
        """
        total = len(file_paths)
        for idx, file_path in enumerate(file_paths):
            self._emit_indexing_progress(idx, total)
            self._index_single_file(file_path, idx, total)

        self.emit_signal(
            SignalCode.RAG_INDEXING_COMPLETE,
            {"success": True, "message": f"Indexed {total} documents"},
        )

    def _emit_indexing_progress(self, idx: int, total: int) -> None:
        """Emit indexing progress signal.

        Args:
            idx: Current document index
            total: Total number of documents
        """
        self.emit_signal(
            SignalCode.RAG_INDEXING_PROGRESS,
            {
                "current": idx,
                "total": total,
                "progress": int((idx / total) * 100),
            },
        )

    def _index_single_file(self, file_path: str, idx: int, total: int) -> None:
        """Index a single document file.

        Args:
            file_path: Path to file to index
            idx: Current index in batch
            total: Total documents in batch
        """
        try:
            db_doc = self._get_document_from_db(file_path)
            if not db_doc:
                return

            self.logger.info(
                f"Indexing document {idx + 1}/{total}: {file_path}"
            )
            agent = (
                getattr(self.model_manager, "agent", None)
                or self.model_manager
            )
            success = agent._index_single_document(db_doc)

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
        """Get document from database.

        Args:
            file_path: Path to document file

        Returns:
            Document object or None if not found
        """
        db_docs = DBDocument.objects.filter_by(path=file_path)
        if not db_docs or len(db_docs) == 0:
            self.logger.warning(f"Document not found in database: {file_path}")
            self._emit_index_failed(
                file_path, "Document not found in database"
            )
            return None
        return db_docs[0]

    def _emit_index_failed(self, path: str, error: str) -> None:
        """Emit document index failed signal.

        Args:
            path: File path that failed
            error: Error message
        """
        self.emit_signal(
            SignalCode.DOCUMENT_INDEX_FAILED,
            {"path": path, "error": error},
        )

    def on_rag_index_cancel_signal(self, data: Dict) -> None:
        """Handle cancel indexing request by setting interrupt flags if available.

        Args:
            data: Signal data dictionary
        """
        try:
            if self.model_manager and hasattr(
                self.model_manager, "do_interrupt"
            ):
                try:
                    self.model_manager.do_interrupt()
                    self.logger.info("Called model_manager.do_interrupt()")
                    return
                except Exception:
                    pass

            agent_or_mgr = (
                getattr(self.model_manager, "agent", None)
                or self.model_manager
            )
            if agent_or_mgr and hasattr(agent_or_mgr, "do_interrupt"):
                try:
                    setattr(agent_or_mgr, "do_interrupt", True)
                    self.logger.info("Set agent_or_mgr.do_interrupt = True")
                except Exception:
                    pass
        except Exception as e:
            self.logger.error(f"Error during cancel indexing: {e}")

    def on_index_document_signal(self, data: Dict) -> None:
        """Handle INDEX_DOCUMENT signal: index file, save index, update DB.

        Args:
            data: Dictionary containing document path
        """
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
        """Validate document path from signal.

        Args:
            path: Path to validate

        Returns:
            True if path is valid
        """
        if not isinstance(path, str) or not path:
            self.logger.warning(
                "INDEX_DOCUMENT signal received with invalid path"
            )
            return False
        return True

    def _process_document_indexing(
        self, path: str, db_doc, filename: str
    ) -> None:
        """Process single document indexing.

        Args:
            path: File path
            db_doc: Database document object
            filename: Name of file
        """
        try:
            self.logger.info(f"Indexing document: {filename}")
            agent = (
                getattr(self.model_manager, "agent", None)
                or self.model_manager
            )
            success = agent._index_single_document(db_doc)

            if success:
                self._handle_indexing_success(path, db_doc, filename)
            else:
                self._handle_indexing_failure(path, filename)

        except Exception as e:
            self.logger.error(
                f"Failed to index document {filename}: {str(e)}", exc_info=True
            )
            self._emit_index_failed(path, str(e))

    def _handle_indexing_success(
        self, path: str, db_doc, filename: str
    ) -> None:
        """Handle successful document indexing.

        Args:
            path: File path
            db_doc: Database document object
            filename: Name of file
        """
        DBDocument.objects.update(pk=db_doc.id, active=True)
        self.logger.info(f"Successfully indexed document: {filename}")
        self.emit_signal(SignalCode.DOCUMENT_INDEXED, {"path": path})

    def _handle_indexing_failure(self, path: str, filename: str) -> None:
        """Handle failed document indexing.

        Args:
            path: File path
            filename: Name of file
        """
        self.logger.error(f"Failed to index document: {filename}")
        self._emit_index_failed(
            path,
            "No content could be extracted from document. "
            "The file may be corrupted, empty, or in an unsupported format.",
        )
