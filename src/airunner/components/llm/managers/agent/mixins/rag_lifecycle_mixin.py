"""RAG Lifecycle management.

This module handles initialization, setup, reloading, and cleanup of the
RAG system components.
"""

import gc
from typing import Optional, List, Dict, Any
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.schema import Document
from bs4 import BeautifulSoup


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

        self._setup_rag()

    def _setup_rag(self):
        """Setup RAG components.

        This method is safe to call multiple times - it will only initialize once.
        It can be called during __init__() or deferred until after model loading.
        """
        try:
            # If the parent/manager has requested to skip agent/RAG load (for
            # example during finetune preparation to conserve GPU memory), then
            # avoid initializing the RAG system which will load embeddings.
            if getattr(self, "_skip_agent_load", False):
                if hasattr(self, "logger"):
                    self.logger.debug(
                        "Skipping RAG setup due to finetune-only mode"
                    )
                return

            # Check if embedding model is available
            # Note: We don't need Settings.llm since LangChain handles chat flow
            # We only need embedding model for document retrieval
            if not hasattr(self, "embedding"):
                if hasattr(self, "logger"):
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

            if hasattr(self, "logger"):
                self.logger.info("RAG system initialized successfully")
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(
                    f"Error setting up RAG: {str(e)}", exc_info=True
                )

    def reload_rag(self):
        """Reload RAG components.

        Clears all caches and resets component state without unloading
        the embedding model. Useful for refreshing indexes after changes.
        """
        if hasattr(self, "logger"):
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
        if hasattr(self, "logger"):
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
        if hasattr(self, "logger"):
            self.logger.debug("Unloading RAG...")
        self._is_unloading = True
        try:
            self.target_files = None

            # Properly unload embedding model
            if self._embedding is not None:
                try:
                    # Try to access and delete the internal model if it exists
                    if hasattr(self._embedding, "_model"):
                        if hasattr(self, "logger"):
                            self.logger.debug(
                                "Deleting embedding internal model..."
                            )
                        del self._embedding._model
                    if hasattr(self._embedding, "model"):
                        if hasattr(self, "logger"):
                            self.logger.debug(
                                "Deleting embedding model attribute..."
                            )
                        del self._embedding.model
                    # Delete the embedding wrapper
                    if hasattr(self, "logger"):
                        self.logger.debug("Deleting embedding wrapper...")
                    del self._embedding
                except Exception as e:
                    if hasattr(self, "logger"):
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

            if self._index:
                self._index.insert(doc)
                if hasattr(self, "logger"):
                    self.logger.info(
                        f"Inserted HTML content '{source_name}' into unified index"
                    )
            else:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        "No index available to insert HTML content"
                    )

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error loading HTML into RAG: {e}")
