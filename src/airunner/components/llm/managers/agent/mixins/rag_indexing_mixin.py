"""RAG document indexing operations.

This mixin provides:
- Single document indexing
- Batch document indexing with progress
- Document reader creation
- Index rebuild functionality
"""

import os
from typing import List, Optional

from llama_index.core import (
    Document,
    VectorStoreIndex,
    SimpleDirectoryReader,
)
from llama_index.readers.file import PDFReader, MarkdownReader

from airunner.components.llm.managers.agent.custom_epub_reader import (
    CustomEpubReader,
)
from airunner.components.llm.managers.agent import HtmlFileReader
from airunner.components.zimreader.llamaindex_zim_reader import (
    LlamaIndexZIMReader,
)
from airunner.components.documents.data.models.document import (
    Document as DBDocument,
)
from airunner.enums import SignalCode


class RAGIndexingMixin:
    """Mixin for RAG document indexing operations."""

    @property
    def document_reader(self) -> Optional[SimpleDirectoryReader]:
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
                self._document_reader = SimpleDirectoryReader(
                    input_files=self.target_files,
                    file_extractor={
                        ".pdf": PDFReader(),
                        ".epub": CustomEpubReader(),
                        ".html": HtmlFileReader(),
                        ".htm": HtmlFileReader(),
                        ".md": MarkdownReader(),
                        ".zim": LlamaIndexZIMReader(),
                    },
                    exclude_hidden=False,
                    file_metadata=self._extract_metadata,
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

            # Enrich with metadata from database
            for doc in documents:
                file_path = doc.metadata.get("file_path")
                if file_path:
                    doc.metadata.update(self._extract_metadata(file_path))

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
            doc_id = self._generate_doc_id(db_doc.path)

            # Load document
            reader = SimpleDirectoryReader(
                input_files=[db_doc.path],
                file_extractor={
                    ".pdf": PDFReader(),
                    ".epub": CustomEpubReader(),
                    ".html": HtmlFileReader(),
                    ".htm": HtmlFileReader(),
                    ".md": MarkdownReader(),
                    ".zim": LlamaIndexZIMReader(),
                },
                file_metadata=self._extract_metadata,
            )

            docs = reader.load_data()
            if not docs:
                self.logger.warning(f"No content extracted from {db_doc.path}")
                return False

            # Enrich with metadata
            for doc in docs:
                doc.metadata.update(self._extract_metadata(db_doc.path))
                doc.metadata["doc_id"] = doc_id

            # Create per-document index
            doc_index = VectorStoreIndex.from_documents(
                docs,
                embed_model=self.embedding,
                show_progress=False,
            )

            # Save to disk
            index_dir = self._get_doc_index_dir(doc_id, db_doc.path)
            os.makedirs(index_dir, exist_ok=True)
            doc_index.storage_context.persist(persist_dir=index_dir)

            # Update registry
            self._update_registry_entry(doc_id, db_doc.path, len(docs))

            # Mark as indexed in DB
            self._mark_document_indexed(db_doc.path)

            self.logger.info(
                f"Indexed document {os.path.basename(db_doc.path)} ({len(docs)} chunks)"
            )
            try:
                self._loaded_doc_ids.append(db_doc.path)
            except Exception:
                pass
            return True

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
