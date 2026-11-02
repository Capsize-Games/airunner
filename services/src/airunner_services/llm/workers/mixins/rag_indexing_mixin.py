"""Service-owned RAG and document indexing operations for the LLM worker."""

import os
import threading
from typing import Dict, List

from airunner_services.database.models.document import Document as DBDocument
from airunner_services.llm.workers.rag_index_status import (
    rag_index_status_tracker,
)
from airunner_services.llm.workers.rag_index_admission import (
    acknowledge_rag_index_job,
    claim_rag_index_job,
    owns_rag_index_job,
    rag_index_cancel_requested,
    release_rag_index_job,
    request_rag_index_cancel,
)
from airunner_services.runtimes.file_policy import (
    PathPolicyError,
    resolve_existing_file,
)
from airunner_services.utils.application.enum_resolver import signal_code_proxy


_DOCUMENT_FILE_SUFFIXES = (
    ".md",
    ".txt",
    ".docx",
    ".doc",
    ".odt",
    ".pdf",
    ".epub",
    ".zim",
)

SignalCode = signal_code_proxy(
    {
        "DOCUMENT_INDEXED": "document_indexed_signal",
        "DOCUMENT_INDEX_FAILED": "document_index_failed_signal",
        "RAG_INDEXING_PROGRESS": "rag_indexing_progress_signal",
        "RAG_INDEXING_COMPLETE": "rag_indexing_complete_signal",
    }
)


class RAGIndexingMixin:
    """Handle RAG indexing requests for the LLM worker."""

    def on_llm_reload_rag_index_signal(self) -> None:
        """Reload the active RAG index when the model manager exists."""
        if self._model_manager:
            self._model_manager.reload_rag_engine()

    def on_rag_index_all_documents_signal(self, data: Dict) -> None:
        """Start indexing all documents on a background thread."""
        token = claim_rag_index_job(data.get("_job_token"))
        if token is None:
            self.logger.warning("Ignoring RAG index request while another job is active")
            return
        self.logger.info("Received RAG_INDEX_ALL_DOCUMENTS signal")
        start_gate = threading.Event()
        indexing_thread = threading.Thread(
            target=self._run_all_documents_job,
            args=(data, token, start_gate),
        )
        try:
            if not owns_rag_index_job(token):
                return
            indexing_thread.start()
        except Exception as exc:
            acknowledge_rag_index_job(token, False)
            if owns_rag_index_job(token):
                self._emit_indexing_error(f"Failed to start indexing: {exc}")
            release_rag_index_job(token)
        else:
            acknowledge_rag_index_job(token, True)
            start_gate.set()

    def _run_all_documents_job(
        self, data: Dict, token: str, start_gate: threading.Event
    ) -> None:
        start_gate.wait()
        if not owns_rag_index_job(token):
            return
        try:
            rag_index_status_tracker.start(
                message="Preparing to index documents...",
            )
            self._index_all_documents_thread(data)
        finally:
            release_rag_index_job(token)

    def _index_all_documents_thread(self, data: Dict) -> None:
        """Run full-document indexing without blocking the caller."""
        if not self._ensure_agent_loaded("indexing"):
            return

        if not self._validate_agent_supports_indexing():
            return

        self._perform_all_documents_indexing()

    def _ensure_agent_loaded(self, operation: str = "operation") -> bool:
        """Ensure the model manager or its agent can perform indexing."""
        if self.model_manager and (
            getattr(self.model_manager, "agent", None)
            or hasattr(self.model_manager, "index_all_documents")
        ):
            return True

        self.logger.info(f"Loading LLM for {operation}...")
        try:
            self.load()
        except Exception as exc:
            self.logger.error(f"Failed to load LLM for {operation}: {exc}")
            self._emit_indexing_error(f"Failed to load LLM: {str(exc)}")
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
        """Return whether the active agent or manager supports full indexing."""
        agent = getattr(self.model_manager, "agent", None) or self.model_manager
        if not hasattr(agent, "index_all_documents"):
            self.logger.error("Agent/manager does not support manual indexing")
            self._emit_indexing_error("Agent does not support indexing")
            return False
        return True

    def _perform_all_documents_indexing(self) -> None:
        """Invoke full-document indexing on the active agent or manager."""
        self.logger.info("Starting manual document indexing with loaded agent")
        try:
            agent = (
                getattr(self.model_manager, "agent", None)
                or self.model_manager
            )
            agent.index_all_documents()
        except Exception as exc:
            self.logger.error(f"Error during indexing: {exc}")
            self._emit_indexing_error(f"Indexing error: {str(exc)}")

    def _emit_indexing_error(self, message: str) -> None:
        """Emit the shared indexing error payload."""
        self.emit_signal(
            SignalCode.RAG_INDEXING_COMPLETE,
            {"success": False, "message": message},
        )

    def on_rag_index_selected_documents_signal(self, data: Dict) -> None:
        """Start indexing one selected list of documents."""
        file_paths = data.get("file_paths", [])
        reindex = bool(data.get("reindex", False))
        if not file_paths:
            self.logger.warning(
                "RAG_INDEX_SELECTED_DOCUMENTS called with no file paths"
            )
            return
        token = claim_rag_index_job(data.get("_job_token"))
        if token is None:
            self.logger.warning(
                "Ignoring selected RAG index request while another job is active"
            )
            return

        self.logger.info(
            "Received RAG_INDEX_SELECTED_DOCUMENTS signal for "
            f"{len(file_paths)} documents"
        )

        start_gate = threading.Event()
        indexing_thread = threading.Thread(
            target=self._run_selected_documents_job,
            args=(file_paths, reindex, token, start_gate),
        )
        try:
            if not owns_rag_index_job(token):
                return
            indexing_thread.start()
        except Exception as exc:
            acknowledge_rag_index_job(token, False)
            if owns_rag_index_job(token):
                self._emit_indexing_error(f"Failed to start indexing: {exc}")
            release_rag_index_job(token)
        else:
            acknowledge_rag_index_job(token, True)
            start_gate.set()

    def _run_selected_documents_job(
        self,
        file_paths: List[str],
        reindex: bool,
        token: str,
        start_gate: threading.Event,
    ) -> None:
        start_gate.wait()
        if not owns_rag_index_job(token):
            return
        try:
            rag_index_status_tracker.start(
                total=len(file_paths),
                message=(
                    "Preparing to reindex documents..."
                    if reindex
                    else "Preparing to index documents..."
                ),
            )
            self._index_selected_documents_thread(file_paths, reindex)
        finally:
            release_rag_index_job(token)

    def _index_selected_documents_thread(
        self, file_paths: List[str], reindex: bool = False
    ) -> None:
        """Run selective indexing without blocking the caller."""
        if not self._ensure_agent_loaded():
            return

        if not self._validate_indexing_support(reindex=reindex):
            return

        self._index_documents(file_paths, reindex=reindex)

    def _validate_indexing_support(self, *, reindex: bool = False) -> bool:
        """Return whether the active agent supports single-document indexing."""
        agent = getattr(self.model_manager, "agent", None) or self.model_manager
        method = (
            "_reindex_single_document"
            if reindex
            else "_index_or_reindex_document"
        )
        if not hasattr(agent, method):
            self.logger.error(
                "Agent/manager does not support %s", method
            )
            self._emit_indexing_error(f"Agent does not support {method}")
            return False
        return True

    def _index_documents(
        self, file_paths: List[str], *, reindex: bool = False
    ) -> None:
        """Index one list of validated document paths."""
        total = len(file_paths)
        indexed_total = 0
        failed_total = 0
        for idx, file_path in enumerate(file_paths):
            if rag_index_cancel_requested():
                self.emit_signal(
                    SignalCode.RAG_INDEXING_COMPLETE,
                    {
                        "success": False,
                        "message": (
                            f"Indexing cancelled after {indexed_total} of "
                            f"{total} document(s)"
                        ),
                    },
                )
                return
            self._emit_indexing_progress(idx, total)
            validated_path = self._validate_document_path(file_path)
            if not validated_path:
                failed_total += 1
                continue
            if self._index_single_file(
                validated_path, idx, total, reindex=reindex
            ):
                indexed_total += 1
            else:
                failed_total += 1

        self.emit_signal(
            SignalCode.RAG_INDEXING_COMPLETE,
            {
                "success": failed_total == 0,
                "message": (
                    f"Indexed {indexed_total} of {total} documents; "
                    f"{failed_total} failed"
                ),
            },
        )

    def _emit_indexing_progress(self, idx: int, total: int) -> None:
        """Emit one indexing progress update."""
        self.emit_signal(
            SignalCode.RAG_INDEXING_PROGRESS,
            {
                "current": idx,
                "total": total,
                "progress": int((idx / total) * 100),
            },
        )

    def _index_single_file(
        self, file_path: str, idx: int, total: int, *, reindex: bool = False
    ) -> bool:
        """Index one document file by path."""
        try:
            db_doc = self._get_document_from_db(file_path)
            if not db_doc:
                return False

            self.logger.info(
                f"Indexing document {idx + 1}/{total}: {file_path}"
            )
            agent = (
                getattr(self.model_manager, "agent", None)
                or self.model_manager
            )
            if reindex:
                success = agent._reindex_single_document(db_doc)
            else:
                success = agent._index_or_reindex_document(db_doc)

            if success:
                if not reindex:
                    DBDocument.objects.update(pk=db_doc.id, active=True)
                self.emit_signal(
                    SignalCode.DOCUMENT_INDEXED,
                    {"path": file_path},
                )
                return True
            else:
                self._emit_index_failed(
                    file_path,
                    "No content could be extracted",
                )
                return False

        except Exception as exc:
            self.logger.error(f"Failed to index {file_path}: {exc}")
            self._emit_index_failed(file_path, str(exc))
            return False

    def _get_document_from_db(self, file_path: str):
        """Return the document record matching one file path."""
        db_docs = DBDocument.objects.filter_by(path=file_path)
        if not db_docs or len(db_docs) == 0:
            self.logger.warning(f"Document not found in database: {file_path}")
            self._emit_index_failed(
                file_path,
                "Document not found in database",
            )
            return None
        return db_docs[0]

    def _emit_index_failed(self, path: str, error: str) -> None:
        """Emit one single-document indexing failure."""
        self.emit_signal(
            SignalCode.DOCUMENT_INDEX_FAILED,
            {"path": path, "error": error},
        )

    def on_rag_index_cancel_signal(self, data: Dict) -> None:
        """Request cancellation of one in-flight indexing operation."""
        request_rag_index_cancel()
        rag_index_status_tracker.cancel_requested()
        try:
            if self.model_manager and hasattr(
                self.model_manager,
                "do_interrupt",
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
        except Exception as exc:
            self.logger.error(f"Error during cancel indexing: {exc}")

    def on_rag_indexing_progress_signal(self, data: Dict) -> None:
        """Mirror one in-flight progress update into daemon status."""
        rag_index_status_tracker.progress(data)

    def on_rag_indexing_complete_signal(self, data: Dict) -> None:
        """Mirror one terminal progress update into daemon status."""
        rag_index_status_tracker.complete(data)

    def on_index_document_signal(self, data: Dict) -> None:
        """Index a single document path from one signal payload."""
        document_path = self._validate_document_path(data.get("path", None))
        if not document_path:
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

    def _validate_document_path(self, path) -> str | None:
        """Validate and normalize one document path from a signal payload."""
        if not isinstance(path, str) or not path:
            self.logger.warning(
                "INDEX_DOCUMENT signal received with invalid path"
            )
            return None
        try:
            return resolve_existing_file(
                path,
                label="Document path",
                allowed_suffixes=_DOCUMENT_FILE_SUFFIXES,
                allowed_roots=self._allowed_document_roots(),
            )
        except PathPolicyError as error:
            self.logger.warning("Rejected document path: %s", error)
            self._emit_index_failed(path, str(error))
            return None

    def _allowed_document_roots(self) -> tuple[str, ...]:
        """Return the allowed filesystem roots for indexing requests."""
        path_settings = getattr(self, "path_settings", None)
        if path_settings is None:
            return ()
        base_path = getattr(path_settings, "base_path", "")
        documents_path = getattr(path_settings, "documents_path", "")
        roots = [documents_path]
        if base_path:
            roots.append(os.path.join(os.path.expanduser(base_path), "zim"))
        return tuple(root for root in roots if root)

    def _process_document_indexing(
        self,
        path: str,
        db_doc,
        filename: str,
    ) -> None:
        """Index one database-backed document record."""
        try:
            self.logger.info(f"Indexing document: {filename}")
            agent = (
                getattr(self.model_manager, "agent", None)
                or self.model_manager
            )
            success = agent._index_or_reindex_document(db_doc)

            if success:
                self._handle_indexing_success(path, db_doc, filename)
            else:
                self._handle_indexing_failure(path, filename)

        except Exception as exc:
            self.logger.error(
                f"Failed to index document {filename}: {str(exc)}",
                exc_info=True,
            )
            self._emit_index_failed(path, str(exc))

    def _handle_indexing_success(
        self,
        path: str,
        db_doc,
        filename: str,
    ) -> None:
        """Finalize one successful document indexing operation."""
        DBDocument.objects.update(pk=db_doc.id, active=True)
        self.logger.info(f"Successfully indexed document: {filename}")
        self.emit_signal(SignalCode.DOCUMENT_INDEXED, {"path": path})

    def _handle_indexing_failure(self, path: str, filename: str) -> None:
        """Finalize one failed document indexing operation."""
        self.logger.error(f"Failed to index document: {filename}")
        self._emit_index_failed(
            path,
            "No content could be extracted from document. "
            "The file may be corrupted, empty, or in an unsupported format.",
        )


__all__ = ["RAGIndexingMixin"]
