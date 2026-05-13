"""RAG lifecycle management."""

import gc
import os
import tempfile
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from langchain_core.documents import Document

from airunner.components.llm.managers.agent.document_loader import (
    DocumentBatchLoader,
    load_documents_from_file,
)
from airunner.components.llm.managers.agent.vector_index import (
    DocumentVectorIndex,
)


class RAGLifecycleMixin:
    """Lifecycle management for RAG system components.

    Handles initialization, setup, reloading, and cleanup of RAG components
    including embedding models, indexes, and caches.
    """

    def __init__(self):
        """Initialize RAG component state variables."""
        self._document_reader: Optional[DocumentBatchLoader] = None
        self._index: Optional[DocumentVectorIndex] = None
        self._retriever: Optional[Any] = None
        self._embedding: Optional[Any] = None
        self._text_splitter: Optional[Any] = None
        self._target_files: Optional[List[str]] = None
        self._doc_metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_validated: bool = False

        self._index_registry: Optional[Dict[str, Any]] = None
        self._doc_indexes_cache: Dict[str, DocumentVectorIndex] = {}
        self._loaded_doc_ids: List[str] = []
        self._rag_initialized = False

    def _setup_rag(self):
        """Setup RAG components.

        This method is safe to call multiple times - it will only initialize once.
        It should be called lazily when RAG is actually needed (e.g., when
        rag_files are provided in a request), not during __init__.
        """
        # Skip if already initialized
        if getattr(self, "_rag_initialized", False):
            return

        try:
            # If the parent/manager has requested to skip agent/RAG load (for
            # example during finetune preparation to conserve GPU memory), then
            # avoid initializing the RAG system which will load embeddings.
            if getattr(self, "_skip_agent_load", False):
                self.logger.debug(
                    "Skipping RAG setup due to finetune-only mode"
                )
                return

            if not hasattr(self, "embedding") or self.embedding is None:
                self.logger.debug(
                    "Deferring RAG setup - embedding model not yet available"
                )
                return

            self._detect_and_migrate_old_index()
            self._rag_initialized = True
            self.logger.info("RAG system initialized successfully")
        except Exception as e:
            self.logger.error(f"Error setting up RAG: {str(e)}", exc_info=True)

    def reload_rag(self):
        """Reload RAG components.

        Clears all caches and resets component state without unloading
        the embedding model. Useful for refreshing indexes after changes.
        """
        self.logger.debug("Reloading RAG...")
        self._index = None
        self._retriever = None
        self._document_reader = None
        self._doc_metadata_cache.clear()
        self._cache_validated = False

        # Clear per-document index caches
        self._doc_indexes_cache.clear()
        self._loaded_doc_ids.clear()
        self._index_registry = None

    def clear_rag_documents(self):
        """Clear all RAG documents and reset components.

        Resets the target files list and reloads RAG components.
        This does not unload the embedding model.
        """
        self.logger.debug("Clearing RAG documents...")
        self.target_files = None
        # Only reload if not in the process of unloading
        if not getattr(self, "_is_unloading", False):
            self.reload_rag()

    def unload_rag(self):
        """Unload all RAG components.

        Completely unloads the RAG system including the embedding model
        to free GPU memory. Use this when switching to finetune mode or
        shutting down.
        """
        self.logger.debug("Unloading RAG...")
        self._is_unloading = True
        try:
            self.target_files = None

            if self._embedding is not None:
                try:
                    del self._embedding
                except Exception as e:
                    self.logger.warning(f"Error deleting embedding: {e}")
            self._embedding = None
            self._text_splitter = None

            # Force garbage collection
            gc.collect()
        finally:
            self._is_unloading = False

    def load_html_into_rag(
        self, html_content: str, source_name: str = "web_content"
    ):
        """Load HTML content into the unified RAG index.

        Parses HTML, extracts text, and inserts into the index with metadata.
        Used for loading web content or HTML documents.

        Args:
            html_content: Raw HTML string
            source_name: Identifier for this content source (e.g., URL)
        """
        try:
            self._setup_rag()
            if self.embedding is None:
                return

            soup = BeautifulSoup(html_content, "html.parser")
            text = soup.get_text(separator="\n", strip=True)

            doc = Document(
                page_content=text,
                metadata={
                    "source": source_name,
                    "doc_id": self._generate_doc_id(source_name),
                    "file_type": ".html",
                },
            )
            self._add_documents_to_unified_index([doc], source_name)

        except Exception as e:
            self.logger.error(f"Error loading HTML into RAG: {e}")

    def load_file_into_rag(self, file_path: str) -> None:
        """Load a local file (PDF/EPUB/HTML/MD/ZIM) into the unified RAG index.

        This will use the configured reader for the file type (e.g. CustomEpubReader
        for .epub), extract the document(s), and insert them into the unified index
        using the same approach as load_html_into_rag.

        Args:
            file_path: Absolute path to a file on disk
        """
        try:
            if not os.path.exists(file_path):
                self.logger.warning(f"File not found: {file_path}")
                return
            if file_path in self._loaded_doc_ids:
                return

            self._setup_rag()
            if self.embedding is None:
                return

            documents = load_documents_from_file(
                file_path,
                self._extract_metadata,
            )
            self._add_documents_to_unified_index(documents, file_path)
        except Exception as e:
            self.logger.error(f"Error loading file into RAG: {e}")

    def load_bytes_into_rag(
        self, content_bytes: bytes, source_name: str, file_ext: str = ".epub"
    ) -> None:
        """Load binary content into RAG, writing to a temporary file first.

        Useful when callers provide raw bytes for EPUB/PDF content instead of
        a file on disk. The data is written to a NamedTemporaryFile with the
        provided extension and then loaded via load_file_into_rag.

        Args:
            content_bytes: Raw file bytes
            source_name: Identifier used in metadata/file name
            file_ext: File extension (e.g. '.epub', '.pdf', '.txt')
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=file_ext, delete=False
            ) as fh:
                fh.write(content_bytes)
                tmp_path = fh.name

            # Reuse file loading logic
            self.load_file_into_rag(tmp_path)
            # Track loaded doc path for temp file
            try:
                self._loaded_doc_ids.append(tmp_path)
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Error loading bytes into RAG: {e}")

    def _add_documents_to_unified_index(
        self,
        documents: list[Document],
        source_id: str,
    ) -> None:
        if not documents:
            return

        if self._index is None:
            self._index = DocumentVectorIndex.from_documents(
                documents,
                self.embedding,
                self.text_splitter,
            )
        else:
            self._index.add_documents(
                documents,
                self.embedding,
                self.text_splitter,
            )

        self._retriever = None
        self._track_loaded_doc(source_id)

    def _track_loaded_doc(self, source_id: str) -> None:
        if source_id not in self._loaded_doc_ids:
            self._loaded_doc_ids.append(source_id)
