"""RAG properties and configuration management.

This mixin provides:
- Property accessors for RAG components
- Configuration path management
- Embedding model setup
- Text splitter configuration
"""

import os
from typing import Optional, Dict, Any
import torch

from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY


class RAGPropertiesMixin:
    """Mixin for RAG properties and configuration."""

    @property
    def text_splitter(self) -> SentenceSplitter:
        """Get or create the text splitter for document chunking.

        Returns:
            Configured SentenceSplitter instance
        """
        if self._text_splitter is None:
            self._text_splitter = SentenceSplitter(
                chunk_size=self.knowledge_settings.chunk_size,
                chunk_overlap=self.knowledge_settings.chunk_overlap,
            )
        return self._text_splitter

    @property
    def doc_indexes_dir(self) -> str:
        """Get the directory path where per-document indexes are stored.

        Returns:
            Absolute path to doc_indexes directory
        """
        base_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "rag",
            "doc_indexes",
        )
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    @property
    def registry_path(self) -> str:
        """Get the path to the index registry JSON file.

        Returns:
            Absolute path to index_registry.json
        """
        return os.path.join(self.doc_indexes_dir, "index_registry.json")

    @property
    def index_registry(self) -> Dict[str, Any]:
        """Get the index registry (lazy load).

        Returns:
            Dictionary mapping doc_id to metadata
        """
        if self._index_registry is None:
            self._index_registry = self._load_registry()
        return self._index_registry

    @property
    def embedding(self) -> HuggingFaceEmbedding:
        """Get or create the embedding model for RAG.

        This is a lazy-loaded property that creates the embedding model
        only when needed and caches it for reuse.

        Returns:
            HuggingFaceEmbedding instance
        """
        if self._embedding is None:
            try:
                device = "cpu"
                if torch.cuda.is_available():
                    device = "cuda"
                elif (
                    hasattr(torch.backends, "mps")
                    and torch.backends.mps.is_available()
                ):
                    device = "mps"

                if hasattr(self, "logger"):
                    self.logger.info(
                        f"Initializing embedding model on {device}: "
                        f"{self.knowledge_settings.embedding_model_name}"
                    )

                # Set quantization flag if using CPU or limited GPU memory
                # This can reduce memory usage significantly
                # quantization_flag = device == "cpu"

                self._embedding = HuggingFaceEmbedding(
                    model_name=self.knowledge_settings.embedding_model_name,
                    device=device,
                    trust_remote_code=True,
                    # embed_batch_size=self.knowledge_settings.embed_batch_size,
                    # text_instruction=self.knowledge_settings.text_instruction,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                )

                if hasattr(self, "logger"):
                    self.logger.info(
                        "Embedding model initialized successfully"
                    )

            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.error(
                        f"Failed to initialize embedding model: {e}",
                        exc_info=True,
                    )
                raise

        return self._embedding

    @property
    def target_files(self) -> Optional[list[str]]:
        """Get the list of target files for indexing.

        Returns:
            List of file paths or None if targeting all documents
        """
        return self._target_files

    @target_files.setter
    def target_files(self, value: Optional[list[str]]):
        """Set the list of target files for indexing.

        Args:
            value: List of file paths or None to target all documents
        """
        self._target_files = value
        if hasattr(self, "logger"):
            if value:
                self.logger.info(f"Set {len(value)} target files for indexing")
            else:
                self.logger.info(
                    "Cleared target files (will index all documents)"
                )

    @property
    def rag_system_prompt(self) -> str:
        """Generate system prompt for RAG-enhanced chat.

        Returns:
            System prompt string with RAG instructions
        """
        return (
            "You are a helpful AI assistant with access to a document database. "
            "When answering questions, use the provided context from the documents "
            "to give accurate, well-sourced responses. If the context doesn't contain "
            "relevant information, acknowledge this and answer based on your general knowledge. "
            "Always cite the document sources when using information from the context."
        )

    @property
    def storage_persist_dir(self) -> str:
        """Get the directory path for persistent RAG storage (legacy).

        This is kept for backward compatibility with the old unified index.

        Returns:
            Absolute path to storage directory
        """
        storage_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "rag",
            "storage",
        )
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir
