"""RAG document indexing operations."""

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document

from airunner_services.llm.managers.agent.document_loader import (
    DocumentBatchLoader,
    iter_document_batches_from_file,
)
from airunner_services.llm.managers.agent.vector_index import (
    DocumentVectorIndex,
)
from airunner_services.database.models.document import (
    Document as DBDocument,
)
from airunner_common.contract_enums import SignalCode
from airunner_services.llm.managers.agent.mixins.runtime_activity import (
    runtime_activity_locked,
)


class ReindexRequiredError(RuntimeError):
    """An automatic initial-index request found persisted index data."""

    code = "reindex_required"


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

    @runtime_activity_locked
    def _index_single_document(self, db_doc: DBDocument) -> bool:
        """Index a single document into its own per-document index.

        Args:
            db_doc: Database document object

        Returns:
            True if indexing succeeded, False otherwise
        """
        try:
            doc_id = self._generate_doc_id(db_doc.path)
            index_paths = (
                self._get_doc_index_dir(doc_id, db_doc.path),
                self._get_legacy_doc_index_dir(doc_id, db_doc.path),
            )
            if any(os.path.exists(path) for path in index_paths):
                raise ReindexRequiredError(
                    "reindex_required: an index directory already exists; "
                    "use the explicit staged reindex operation"
                )

            self._setup_rag()
            if self.embedding is None:
                return False

            doc_index = None
            for batch in iter_document_batches_from_file(
                db_doc.path, self._extract_metadata
            ):
                for doc in batch:
                    doc.metadata.update(self._extract_metadata(db_doc.path))
                    doc.metadata["doc_id"] = doc_id

                if doc_index is None:
                    doc_index = DocumentVectorIndex.from_documents(
                        batch, self.embedding, self.text_splitter
                    )
                else:
                    doc_index.add_documents(
                        batch, self.embedding, self.text_splitter
                    )

            if doc_index is None:
                self.logger.warning(f"No content extracted from {db_doc.path}")
                return False

            index_dir = self._get_doc_index_dir(doc_id, db_doc.path)
            os.makedirs(index_dir, exist_ok=True)
            doc_index.persist(index_dir)

            self._update_registry_entry(
                doc_id, db_doc.path, len(doc_index.documents)
            )
            self._mark_document_indexed(db_doc.path)

            self.logger.info(
                f"Indexed document {os.path.basename(db_doc.path)} "
                f"({len(doc_index.documents)} chunks)"
            )
            try:
                self._loaded_doc_ids.append(db_doc.path)
            except Exception:
                pass
            return True

        except Exception as e:
            if isinstance(e, ReindexRequiredError):
                raise
            self.logger.error(f"Failed to index {db_doc.path}: {e}")
            return False

    def _index_or_reindex_document(self, db_doc: DBDocument) -> bool:
        """Explicitly index a new document or stage-reindex an existing one."""
        doc_id = self._generate_doc_id(db_doc.path)
        index_paths = (
            self._get_doc_index_dir(doc_id, db_doc.path),
            self._get_legacy_doc_index_dir(doc_id, db_doc.path),
        )
        existing_paths = [path for path in index_paths if os.path.exists(path)]
        if not existing_paths:
            return self._index_single_document(db_doc)

        persisted_path = self._resolve_doc_index_dir(doc_id, db_doc.path)
        if persisted_path is None:
            self.logger.error(
                "reindex_required: existing index directory is not a valid "
                "persisted index for %s", db_doc.path
            )
            return False
        return self._reindex_single_document(db_doc)

    @runtime_activity_locked
    def _reindex_single_document(self, db_doc: DBDocument) -> bool:
        """Rebuild one existing index and switch it only after validation."""
        doc_id = self._generate_doc_id(db_doc.path)
        index_dir = self._resolve_doc_index_dir(doc_id, db_doc.path)
        if index_dir is None:
            self.logger.error(
                "Cannot reindex %s because no persisted index exists", db_doc.path
            )
            return False

        registry_before = copy.deepcopy(self.index_registry)
        registry_path = self.registry_path
        registry_before_bytes = (
            Path(registry_path).read_bytes()
            if os.path.exists(registry_path)
            else None
        )
        old_db_state = {
            field: getattr(db_doc, field, None)
            for field in ("indexed", "file_hash", "indexed_at", "file_size")
        }
        backup_dir = None
        try:
            self._setup_rag()
            embedding = self.embedding
            if embedding is None:
                return False
            source_file_hash = self._calculate_file_hash(db_doc.path)
            if not source_file_hash:
                raise ValueError("source file is unavailable for reindex")
            source_file_size = os.path.getsize(db_doc.path)

            candidate = None
            for batch in iter_document_batches_from_file(
                db_doc.path, self._extract_metadata
            ):
                for document in batch:
                    document.metadata.update(self._extract_metadata(db_doc.path))
                    document.metadata["doc_id"] = doc_id
                if candidate is None:
                    candidate = DocumentVectorIndex.from_documents(
                        batch, embedding, self.text_splitter
                    )
                else:
                    candidate.add_documents(batch, embedding, self.text_splitter)

            if candidate is None or not candidate.documents:
                raise ValueError("no content extracted for staged reindex")

            if self._calculate_file_hash(db_doc.path) != source_file_hash:
                raise RuntimeError(
                    "source file changed while reindex embeddings were built"
                )

            backup_dir = candidate.replace_persisted_atomically(index_dir)
            if backup_dir is None:
                raise RuntimeError("reindex did not retain the previous index")

            self._update_registry_entry(
                doc_id, db_doc.path, len(candidate.documents),
                file_hash=source_file_hash,
            )
            with open(self.registry_path, "r", encoding="utf-8") as registry_file:
                persisted_registry = json.load(registry_file)
            entry = persisted_registry.get("documents", {}).get(doc_id, {})
            if (
                entry.get("path") != db_doc.path
                or entry.get("chunk_count") != len(candidate.documents)
                or entry.get("file_hash") != source_file_hash
            ):
                raise RuntimeError("reindex registry update did not persist")

            self._mark_document_indexed(
                db_doc.path,
                file_hash=source_file_hash,
                file_size=source_file_size,
            )
            current_records = DBDocument.objects.filter_by(path=db_doc.path)
            current_record = current_records[0] if current_records else None
            if (
                current_record is None
                or not getattr(current_record, "indexed", False)
                or getattr(current_record, "file_hash", None) != source_file_hash
            ):
                raise RuntimeError("reindex database status did not persist")

            self._unload_doc_index(doc_id)
            self.logger.info(
                "Reindexed document %s (%d chunks); previous index retained at %s",
                os.path.basename(db_doc.path),
                len(candidate.documents),
                backup_dir,
            )
            return True
        except Exception as exc:
            self.logger.error("Failed to reindex %s: %s", db_doc.path, exc)
            if backup_dir is not None:
                try:
                    DocumentVectorIndex.restore_persisted_backup(
                        index_dir, backup_dir
                    )
                except Exception as rollback_exc:
                    self.logger.critical(
                        "Failed to restore previous index for %s: %s",
                        db_doc.path,
                        rollback_exc,
                    )
            self._index_registry = registry_before
            try:
                _restore_registry_file(registry_path, registry_before_bytes)
            except Exception as rollback_exc:
                self.logger.critical(
                    "Failed to restore reindex registry for %s: %s",
                    db_doc.path,
                    rollback_exc,
                )
            try:
                DBDocument.objects.update(pk=db_doc.id, **old_db_state)
            except Exception as rollback_exc:
                self.logger.critical(
                    "Failed to restore document metadata for %s: %s",
                    db_doc.path,
                    rollback_exc,
                )
            return False


    @runtime_activity_locked
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

        # Lazy initialize RAG system (loads embedding model)
        if hasattr(self, "_setup_rag"):
            self._setup_rag()

        success = True
        for path in file_paths:
            # Skip if already tracked as loaded/indexed
            try:
                if path in getattr(self, "_loaded_doc_ids", []):
                    self.logger.debug(f"Skipping already indexed path: {path}")
                    continue
            except Exception:
                pass

            if not os.path.exists(path):
                self.logger.warning(
                    f"File does not exist for indexing: {path}"
                )
                success = False
                continue

            # Use the load_file_into_rag to index - it will update _loaded_doc_ids
            try:
                self.logger.info(f"Ensuring indexing for file: {path}")
                self.load_file_into_rag(path)
            except Exception as e:
                self.logger.error(f"Failed to ensure index for {path}: {e}")
                success = False

        # Recreate retriever after any indexing operations
        try:
            self._retriever = None
        except Exception:
            pass
        return success

    @runtime_activity_locked
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
                if self._index_or_reindex_document(db_doc):
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


def _restore_registry_file(path: str, contents: bytes | None) -> None:
    """Restore the exact registry bytes after a failed index transaction."""
    if contents is None:
        if os.path.exists(path):
            os.unlink(path)
        return
    parent = os.path.dirname(path)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".registry-restore-", dir=parent
    )
    try:
        with os.fdopen(descriptor, "wb") as registry_file:
            registry_file.write(contents)
            registry_file.flush()
            os.fsync(registry_file.fileno())
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
