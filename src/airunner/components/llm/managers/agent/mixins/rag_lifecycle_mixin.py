"""RAG Lifecycle management.

This module handles initialization, setup, reloading, and cleanup of the
RAG system components.
"""

import gc
import os
from typing import Optional, List, Dict, Any
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.schema import Document
from bs4 import BeautifulSoup
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.readers.file import PDFReader, MarkdownReader
from airunner.components.llm.managers.agent.custom_epub_reader import (
    CustomEpubReader,
)
from airunner.components.llm.managers.agent.html_file_reader import (
    HtmlFileReader,
)
from airunner.components.zimreader.llamaindex_zim_reader import (
    LlamaIndexZIMReader,
)
import tempfile


class RAGLifecycleMixin:
    """Lifecycle management for RAG system components.

    Handles initialization, setup, reloading, and cleanup of RAG components
    including embedding models, indexes, and caches.
    """

    def __init__(self):
        """Initialize RAG component state variables."""
        from llama_index.core.readers import SimpleDirectoryReader
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.core.retrievers import VectorIndexRetriever
        from llama_index.core.node_parser import SentenceSplitter

        self._document_reader: Optional[SimpleDirectoryReader] = None
        self._index: Optional[VectorStoreIndex] = None
        self._retriever: Optional[VectorIndexRetriever] = None
        self._embedding: Optional[HuggingFaceEmbedding] = None
        # NOTE: RAG engine not used - LangChain handles chat flow
        # self._rag_engine: Optional[ConversationAwareContextChatEngine] = None
        # self._rag_engine_tool: Optional[Any] = None
        self._text_splitter: Optional[SentenceSplitter] = None
        self._target_files: Optional[List[str]] = None
        self._doc_metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_validated: bool = False

        # Per-document index architecture
        self._index_registry: Optional[Dict[str, Any]] = None
        self._doc_indexes_cache: Dict[str, VectorStoreIndex] = {}
        self._loaded_doc_ids: List[str] = []

        # NOTE: _setup_rag() is NOT called here anymore.
        # Embedding model loading is deferred until RAG is actually used
        # to avoid loading ~1.3GB into VRAM when RAG isn't needed.
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

            # Check if embedding model is available
            # Note: We don't need Settings.llm since LangChain handles chat flow
            # We only need embedding model for document retrieval
            if not hasattr(self, "embedding") or self.embedding is None:
                self.logger.debug(
                    "Deferring RAG setup - embedding model not yet available"
                )
                return

            # Set up LlamaIndex settings
            # Only set embedding and text splitter - LangChain handles LLM
            Settings.embed_model = self.embedding
            Settings.node_parser = self.text_splitter

            # Check for old unified index and migrate if needed
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
        self._rag_engine = None
        self._document_reader = None
        self._rag_engine_tool = None
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

            # Properly unload embedding model
            if self._embedding is not None:
                try:
                    # Try to access and delete the internal model if it exists
                    if hasattr(self._embedding, "_model"):
                        self.logger.debug(
                            "Deleting embedding internal model..."
                        )
                        del self._embedding._model
                    if hasattr(self._embedding, "model"):
                        self.logger.debug(
                            "Deleting embedding model attribute..."
                        )
                        del self._embedding.model
                    # Delete the embedding wrapper
                    self.logger.debug("Deleting embedding wrapper...")
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
            soup = BeautifulSoup(html_content, "html.parser")
            text = soup.get_text(separator="\n", strip=True)

            doc = Document(
                text=text,
                metadata={
                    "source": source_name,
                    "doc_id": self._generate_doc_id(source_name),
                    "file_type": ".html",
                },
            )

            # Create index if it doesn't exist
            if not self._index:
                self.logger.info("Creating new RAG index for HTML content")
                self._index = VectorStoreIndex.from_documents(
                    [doc],
                    embed_model=self.embedding,
                    show_progress=False,
                )
                self.logger.info(
                    f"Created index with HTML content '{source_name}'"
                )
            else:
                self._index.insert(doc)
                self.logger.info(
                    f"Inserted HTML content '{source_name}' into unified index"
                )

            # CRITICAL: Clear retriever so it gets recreated with the new index
            self._retriever = None
            # Track loaded source so future checks can skip reindex
            try:
                self._loaded_doc_ids.append(source_name)
            except Exception as e:
                self.logger.error(f"Error tracking loaded doc ID: {e}")

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
            reader = SimpleDirectoryReader(
                input_files=[file_path],
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

            documents = reader.load_data()
            # Enrich metadata and insert into unified index
            for doc in documents:
                file_path_meta = doc.metadata.get("file_path")
                if file_path_meta:
                    doc.metadata.update(self._extract_metadata(file_path_meta))

                if not self._index:
                    # create unified index from first document
                    self._index = VectorStoreIndex.from_documents(
                        [doc], embed_model=self.embedding, show_progress=False
                    )
                    self.logger.info(
                        f"Created unified index with content from {file_path}"
                    )
                else:
                    self._index.insert(doc)

                    self.logger.info(
                        f"Inserted content from {file_path} into unified index"
                    )

            # Clear retriever to ensure it's rebuilt against the new index
            self._retriever = None
            # Track loaded doc path
            try:
                self._loaded_doc_ids.append(file_path)
            except Exception:
                pass
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
