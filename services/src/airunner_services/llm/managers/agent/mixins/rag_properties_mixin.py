"""RAG properties and configuration management."""

import os
from typing import Any, Dict, Optional

import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from airunner_services.llm.managers.agent.mixins.runtime_activity import (
    runtime_activity_locked,
)

class RAGPropertiesMixin:
    """Mixin for RAG properties and configuration."""

    @property
    def text_splitter(self) -> RecursiveCharacterTextSplitter:
        """Get or create the text splitter for document chunking.

        Returns:
            Configured SentenceSplitter instance
        """
        if self._text_splitter is None:
            # Get RAG settings with safe defaults
            rag_settings = getattr(self, "rag_settings", None)
            chunk_size = 512  # default
            chunk_overlap = 50  # default

            if rag_settings is not None:
                chunk_size = getattr(rag_settings, "chunk_size", 512)
                chunk_overlap = getattr(rag_settings, "chunk_overlap", 50)

            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        return self._text_splitter

    @property
    def rag_storage_root(self) -> str:
        """Return the configured root for persisted RAG data."""
        configured = getattr(self.path_settings, "rag_index_path", None)
        if configured:
            return os.path.expanduser(configured)
        return self.legacy_rag_storage_root

    @property
    def legacy_rag_storage_root(self) -> str:
        """Return the legacy root used by older per-document indexes."""
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "rag",
        )

    @property
    def doc_indexes_dir(self) -> str:
        """Get the directory path where per-document indexes are stored.

        Returns:
            Absolute path to doc_indexes directory
        """
        base_dir = os.path.join(self.rag_storage_root, "doc_indexes")
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    @property
    def legacy_doc_indexes_dir(self) -> str:
        """Return the legacy per-document index directory."""
        return os.path.join(self.legacy_rag_storage_root, "doc_indexes")

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
    @runtime_activity_locked
    def embedding(self) -> Optional[HuggingFaceEmbeddings]:
        """Get or create the embedding model for RAG.

        This is a lazy-loaded property that creates the embedding model
        only when needed and caches it for reuse.

        Returns:
            HuggingFaceEmbedding instance
        """
        if self._embedding is None:
            endpoint = (os.environ.get("AIRUNNER_EMBED_ENDPOINT")
                        or "").strip()
            if endpoint:
                # Opt-in: run embeddings on another machine (e.g. mx's
                # RTX 2080 SUPER) so this GPU is kept for the LLM. Unset
                # the env var to restore the original local behaviour.
                from langchain_ollama import OllamaEmbeddings

                self._embedding = OllamaEmbeddings(
                    base_url=endpoint,
                    model=os.environ.get(
                        "AIRUNNER_EMBED_MODEL", "qwen3-embedding:8b"),
                )
                self.logger.info(
                    "Using remote embedding endpoint %s", endpoint)
                return self._embedding
            try:
                # Construct local path to embedding model files
                # Must use local filesystem path, not HuggingFace repo ID
                model_name = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "text",
                        "models",
                        "llm",
                        "embedding",
                        "intfloat/e5-large",
                    )
                )

                # Bind the model to the reviewed immutable files before
                # constructing the runtime. The verifier rejects mutable or
                # unexpected artifacts and never imports code from this path.
                from airunner_services.runtimes.e5_model_identity import (
                    E5ModelIdentityError,
                    VerifiedE5Embedder,
                    verify_e5_model_directory,
                )

                try:
                    verified_identity = verify_e5_model_directory(model_name)
                except (E5ModelIdentityError, OSError) as exc:
                    self.logger.warning(
                        "Local E5 embedding is unavailable: model files are "
                        "missing or do not match the reviewed manifest (%s)",
                        exc,
                    )
                    return None

                device = "cpu"
                if torch.cuda.is_available():
                    device = "cuda"
                elif (
                    hasattr(torch.backends, "mps")
                    and torch.backends.mps.is_available()
                ):
                    device = "mps"

                self.logger.info(
                    f"Initializing embedding model on {device}: "
                    f"{model_name}"
                )

                model_kwargs = {}
                model_kwargs["device"] = device
                # intfloat/e5-large is natively supported; do not execute
                # code shipped inside a downloaded model repo.
                model_kwargs["trust_remote_code"] = False
                model_kwargs["local_files_only"] = True

                raw_embedder = HuggingFaceEmbeddings(
                    model_name=model_name,
                    model_kwargs=model_kwargs,
                    encode_kwargs={"normalize_embeddings": True},
                )
                self._embedding = VerifiedE5Embedder(
                    raw_embedder,
                    verified_identity,
                    activity_lock=getattr(self, "runtime_activity_lock", None),
                )

                self.logger.info("Embedding model initialized successfully")

            except Exception as e:
                self.logger.error(
                    f"Failed to initialize embedding model: {e}",
                    exc_info=True,
                )
                # Don't raise - return None to allow RAG setup to skip gracefully
                return None

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
        if value:
            self.logger.info(f"Set {len(value)} target files for indexing")
        else:
            self.logger.info("Cleared target files (will index all documents)")

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
        storage_dir = os.path.join(self.rag_storage_root, "storage")
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir

    @property
    def legacy_storage_persist_dir(self) -> str:
        """Return the legacy unified-index storage directory."""
        return os.path.join(self.legacy_rag_storage_root, "storage")
