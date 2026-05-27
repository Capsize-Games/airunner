"""RAG document indexing operations."""

import os
from typing import List, Optional

from langchain_core.documents import Document

from airunner.components.llm.managers.agent.document_loader import (
    DocumentBatchLoader,
    load_documents_from_file,
)
from airunner.components.llm.managers.agent.vector_index import (
    DocumentVectorIndex,
)
from airunner.models.document import (
    Document as DBDocument,
)
from airunner.enums import SignalCode


class EmbeddingModelDownloadPendingError(RuntimeError):
    """Raised when indexing must wait for the embedding model download."""


class RAGIndexingMixin:
    """Mixin for RAG document indexing operations."""

    @property
    def document_reader(self) -> Optional[DocumentBatchLoader]:
        """Get document reader for all indexed files.

        Returns:
            SimpleDirectoryReader instance or None if no target files
        """
        if not self.target_files:
            self.logger.debug("No target files specified")
            return None

        if not self._document_reader:
            self.logger.debug(
                f"Creating unified document reader for {len(self.target_files)} files"
            )
            try:
                self._document_reader = DocumentBatchLoader(
                    input_files=self.target_files,
                    metadata_loader=self._extract_metadata,
                )
                self.logger.debug("Document reader created successfully")
            except Exception as e:
                self.logger.error(f"Error creating document reader: {str(e)}")
                return None
        return self._document_reader

    @property
    def documents(self) -> List[Document]:
        """Load all documents with rich metadata.

        Returns:
            List of Document instances with metadata
        """
        if not self.document_reader:
            self.logger.debug("No document reader available")
            return []

        try:
            documents = self.document_reader.load_data()
            self.logger.debug(
                f"Loaded {len(documents)} documents with metadata"
            )
            return documents
        except Exception as e:
            self.logger.error(f"Error loading documents: {e}")
            return []

    def _index_single_document(self, db_doc: DBDocument) -> bool:
        """Index a single document into its own per-document index.

        Args:
            db_doc: Database document object

        Returns:
            True if indexing succeeded, False otherwise
        """
        try:
            self._setup_rag()
            embedding = self.embedding
            if embedding is None:
                if getattr(self, "_embedding_download_pending", False):
                    raise EmbeddingModelDownloadPendingError(
                        "Embedding model download in progress."
                    )
                return False

            doc_id = self._generate_doc_id(db_doc.path)

            docs = load_documents_from_file(db_doc.path, self._extract_metadata)
            if not docs:
                self.logger.warning(f"No content extracted from {db_doc.path}")
                return False
            for doc in docs:
                doc.metadata.update(self._extract_metadata(db_doc.path))
                doc.metadata["doc_id"] = doc_id

            doc_index = DocumentVectorIndex.from_documents(
                docs,
                embedding,
                self.text_splitter,
            )

            index_dir = self._get_doc_index_dir(doc_id, db_doc.path)
            os.makedirs(index_dir, exist_ok=True)
            doc_index.persist(index_dir)

            self._update_registry_entry(doc_id, db_doc.path, len(docs))
            self._mark_document_indexed(db_doc.path)

            self.logger.info(
                f"Indexed document {os.path.basename(db_doc.path)} ({len(docs)} chunks)"
            )
            try:
                self._loaded_doc_ids.append(db_doc.path)
            except Exception:
                pass
            return True

        except EmbeddingModelDownloadPendingError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to index {db_doc.path}: {e}")
            return False

    def ensure_indexed_files(self, file_paths: List[str]) -> bool:
        """Ensure that the given file paths have been loaded/indexed.

        This method will load files into the RAG index synchronously if they
        are not already present. It returns True if at least one file was
        indexed or all files were already indexed. It returns False only if
        one or more indexing operations failed.
        
        NOTE: This triggers lazy RAG initialization if not already done.
        """
        if not file_paths:
            self.logger.debug("No file paths provided to ensure_indexed_files")
            return True

        self._rag_retry_after_download = False
        self._last_rag_index_error = None

        # Lazy initialize RAG system (loads embedding model)
        if hasattr(self, "_setup_rag"):
            self._setup_rag()

        success = True
        indexed_paths: List[str] = []
        changed_paths: List[str] = []
        for path in file_paths:
            try:
                ok, indexed_now, changed, event_path = (
                    self._ensure_request_document_ready(path)
                )
            except EmbeddingModelDownloadPendingError as error:
                success = False
                self._rag_retry_after_download = True
                self._last_rag_index_error = str(error)
                self.logger.info(
                    "Deferring request document indexing for %s until "
                    "embedding download completes",
                    path,
                )
                break
            if not ok:
                success = False
                continue
            if indexed_now and event_path not in indexed_paths:
                indexed_paths.append(event_path)
            if changed and event_path not in changed_paths:
                changed_paths.append(event_path)

        # Recreate retriever after any indexing operations
        try:
            self._retriever = None
        except Exception:
            pass

        self._emit_request_document_updates(indexed_paths, changed_paths)
        return success

    def _ensure_request_document_ready(
        self,
        path: str,
    ) -> tuple[bool, bool, bool, str]:
        """Persist one request-attached file into indexed/active document state."""
        resolved_path = self._resolve_request_document_path(path)
        if not os.path.exists(resolved_path):
            self.logger.warning(
                "File does not exist for indexing: %s",
                path,
            )
            return False, False, False, path

        db_doc, created = self._get_or_create_request_document(resolved_path)
        if db_doc is None:
            return False, False, False, resolved_path

        was_indexed = bool(getattr(db_doc, "indexed", False))
        was_active = bool(getattr(db_doc, "active", False))
        if not was_indexed:
            self.logger.info(
                "Ensuring indexing for file: %s",
                resolved_path,
            )
            if not self._index_single_document(db_doc):
                self.logger.error(
                    "Failed to ensure index for %s",
                    resolved_path,
                )
                return False, False, False, resolved_path
            refreshed_docs = DBDocument.objects.filter_by(
                path=resolved_path
            )
            if refreshed_docs:
                db_doc = refreshed_docs[0]

        if not was_active:
            DBDocument.objects.update(pk=db_doc.id, active=True)

        changed = created or not was_indexed or not was_active
        return True, not was_indexed, changed, db_doc.path

    def _resolve_request_document_path(self, path: str) -> str:
        """Return the best existing managed path for one request document."""
        normalized_path = os.path.normpath(os.path.expanduser(path))
        if os.path.exists(normalized_path):
            return normalized_path

        db_doc = self._find_existing_request_document(normalized_path)
        if db_doc is None:
            return normalized_path

        self.logger.info(
            "Resolved missing request document %s to %s",
            path,
            db_doc.path,
        )
        return db_doc.path

    def _find_existing_request_document(self, path: str):
        """Find one existing document row for a missing request path."""
        db_docs = DBDocument.objects.filter_by(path=path)
        if db_docs and len(db_docs) > 0:
            return db_docs[0]

        file_name = os.path.basename(path)
        try:
            for db_doc in DBDocument.objects.all():
                doc_path = getattr(db_doc, "path", "")
                if not doc_path:
                    continue
                if os.path.basename(doc_path) != file_name:
                    continue
                if os.path.exists(doc_path):
                    return db_doc
        except Exception as error:
            self.logger.debug(
                "Failed to resolve managed request document %s: %s",
                path,
                error,
            )
        return None

    def _get_or_create_request_document(self, path: str):
        """Return one document row for request-attached indexing."""
        db_docs = DBDocument.objects.filter_by(path=path)
        if db_docs and len(db_docs) > 0:
            return db_docs[0], False

        try:
            db_doc = DBDocument.objects.create(
                path=path,
                active=False,
                indexed=False,
            )
        except Exception as error:
            self.logger.error(
                "Failed to create document record for %s: %s",
                path,
                error,
            )
            return None, False
        return db_doc, True

    def _emit_request_document_updates(
        self,
        indexed_paths: List[str],
        changed_paths: List[str],
    ) -> None:
        """Notify GUI consumers when request-attached docs changed state."""
        emitter = getattr(self, "emit_signal", None)
        if not callable(emitter):
            return

        for path in indexed_paths:
            emitter(SignalCode.DOCUMENT_INDEXED, {"path": path})
        if changed_paths:
            emitter(
                SignalCode.DOCUMENT_COLLECTION_CHANGED,
                {"paths": changed_paths},
            )

    def index_all_documents(self) -> bool:
        """Manually index all documents with progress reporting.

        Uses per-document architecture for scalability.

        Returns:
            True if indexing succeeded, False otherwise
        """
        try:
            self.logger.info(
                "=== Starting per-document indexing (index_all_documents called) ==="
            )

            # Emit initial progress signal
            self.logger.info("Emitting initial RAG_INDEXING_PROGRESS signal")
            self.emit_signal(
                SignalCode.RAG_INDEXING_PROGRESS,
                {
                    "progress": 0,
                    "current": 0,
                    "total": 0,
                    "document_name": "Preparing to index...",
                },
            )

            # Get all unindexed documents
            self.logger.info("Getting list of unindexed documents...")
            unindexed_docs = self._get_unindexed_documents()
            total_docs = len(unindexed_docs)
            self.logger.info(f"Found {total_docs} unindexed documents")

            if total_docs == 0:
                self.logger.info("No documents need indexing")
                self.emit_signal(
                    SignalCode.RAG_INDEXING_COMPLETE,
                    {
                        "success": True,
                        "message": "All documents already indexed",
                    },
                )
                return True

            # Reset any previous interrupt flag
            try:
                if hasattr(self, "do_interrupt"):
                    setattr(self, "do_interrupt", False)
            except Exception:
                pass

            # Index each document separately
            success_count = 0
            for idx, db_doc in enumerate(unindexed_docs, 1):
                # Check for external interrupt/cancel request
                if getattr(self, "do_interrupt", False):
                    self.logger.info("Indexing interrupted by user")
                    self.emit_signal(
                        SignalCode.RAG_INDEXING_COMPLETE,
                        {
                            "success": False,
                            "message": f"Indexing cancelled by user ({success_count}/{total_docs} completed)",
                        },
                    )
                    # Reset flag
                    try:
                        setattr(self, "do_interrupt", False)
                    except Exception:
                        pass
                    return False

                if not os.path.exists(db_doc.path):
                    self.logger.warning(f"Document not found: {db_doc.path}")
                    continue

                # Emit progress
                doc_name = os.path.basename(db_doc.path)
                progress_data = {
                    "current": idx,
                    "total": total_docs,
                    "progress": min((idx / total_docs) * 100, 99),
                    "document_name": doc_name,
                }
                self.logger.debug(
                    f"Emitting RAG_INDEXING_PROGRESS: {progress_data}"
                )
                self.emit_signal(
                    SignalCode.RAG_INDEXING_PROGRESS,
                    progress_data,
                )

                self.logger.info(
                    f"Indexing ({idx}/{total_docs}): {db_doc.path}"
                )

                # Index the document
                if self._index_single_document(db_doc):
                    success_count += 1

            # Emit completion
            self._cache_validated = True

            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {
                    "success": True,
                    "message": f"Successfully indexed {success_count}/{total_docs} document(s)",
                },
            )

            self.logger.info(
                f"Per-document indexing complete: {success_count}/{total_docs} documents indexed"
            )
            return success_count > 0

        except Exception as e:
            self.logger.error(f"Error during per-document indexing: {e}")
            self.emit_signal(
                SignalCode.RAG_INDEXING_COMPLETE,
                {
                    "success": False,
                    "message": f"Indexing failed: {str(e)}",
                },
            )
            # Ensure interrupt flag cleared on failure
            try:
                if hasattr(self, "do_interrupt"):
                    setattr(self, "do_interrupt", False)
            except Exception:
                pass
            return False
