"""RAG properties and configuration management."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY


_EMBEDDING_REPO_ID = "intfloat/e5-large"
_RAG_EMBEDDING_MODEL_TYPE = "rag_embedding"
_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "


def _apply_embedding_prefix(text: str, prefix: str) -> str:
    """Return text with one E5-compatible prefix when needed."""
    value = str(text or "")
    lowered = value.lstrip().lower()
    if lowered.startswith(_QUERY_PREFIX) or lowered.startswith(
        _PASSAGE_PREFIX
    ):
        return value
    return f"{prefix}{value}"


class _PrefixedEmbeddingAdapter:
    """Delegate embedding calls while applying model-specific prefixes."""

    def __init__(
        self,
        backend: HuggingFaceEmbeddings,
        *,
        query_prefix: str = "",
        document_prefix: str = "",
    ) -> None:
        self._backend = backend
        self._query_prefix = query_prefix
        self._document_prefix = document_prefix

    def embed_query(self, text: str):
        """Embed one retrieval query with the configured query prefix."""
        prepared = text
        if self._query_prefix:
            prepared = _apply_embedding_prefix(text, self._query_prefix)
        return self._backend.embed_query(prepared)

    def embed_documents(self, texts: Sequence[str]):
        """Embed retrieval passages with the configured passage prefix."""
        prepared = list(texts)
        if self._document_prefix:
            prepared = [
                _apply_embedding_prefix(text, self._document_prefix)
                for text in texts
            ]
        return self._backend.embed_documents(prepared)

    def __getattr__(self, name: str) -> Any:
        """Forward all other attributes to the wrapped embeddings backend."""
        return getattr(self._backend, name)


class RAGPropertiesMixin:
    """Mixin for RAG properties and configuration."""

    def _embedding_model_path(self) -> str:
        """Return the local filesystem path for the RAG embedding model."""
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "models",
                "llm",
                "embedding",
                _EMBEDDING_REPO_ID,
            )
        )

    def _set_embedding_resource_state(self, state: str) -> None:
        """Mirror one embedding runtime state into ModelResourceManager."""
        try:
            from airunner.components.model_management.model_resource_manager import (
                ModelResourceManager,
            )
            from airunner.components.model_management.types import ModelState
        except Exception:
            return

        manager = ModelResourceManager()
        model_id = self._embedding_model_path()
        if state == "loading":
            manager.set_model_state(
                model_id,
                ModelState.LOADING,
                _RAG_EMBEDDING_MODEL_TYPE,
            )
            return
        if state == "loaded":
            manager.model_loaded(model_id, _RAG_EMBEDDING_MODEL_TYPE)
            return
        manager.cleanup_model(model_id, _RAG_EMBEDDING_MODEL_TYPE)

    def _wrap_embedding_backend(
        self,
        backend: HuggingFaceEmbeddings,
    ) -> Any:
        """Return the configured embedding backend with RAG-specific tweaks."""
        model_path = self._embedding_model_path().lower()
        if model_path.endswith("e5-large"):
            return _PrefixedEmbeddingAdapter(
                backend,
                query_prefix=_QUERY_PREFIX,
                document_prefix=_PASSAGE_PREFIX,
            )
        return backend

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
    def embedding(self) -> Optional[HuggingFaceEmbeddings]:
        """Get or create the embedding model for RAG.

        This is a lazy-loaded property that creates the embedding model
        only when needed and caches it for reuse.

        Returns:
            HuggingFaceEmbedding instance
        """
        if self._embedding is None:
            try:
                model_name = self._embedding_model_path()
                self._set_embedding_resource_state("loading")

                # Check if model files exist and trigger download if needed
                if not self._check_and_download_embedding_model(model_name):
                    self.logger.warning(
                        "Embedding model files missing - download in progress"
                    )
                    return None

                self._ensure_local_embedding_metadata(model_name)

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
                model_kwargs["trust_remote_code"] = True
                model_kwargs["local_files_only"] = AIRUNNER_LOCAL_FILES_ONLY

                backend = HuggingFaceEmbeddings(
                    model_name=model_name,
                    model_kwargs=model_kwargs,
                    encode_kwargs={"normalize_embeddings": True},
                )
                self._embedding = self._wrap_embedding_backend(backend)
                self._set_embedding_resource_state("loaded")

                self.logger.info("Embedding model initialized successfully")

            except Exception as e:
                self._set_embedding_resource_state("unloaded")
                self.logger.error(
                    f"Failed to initialize embedding model: {e}",
                    exc_info=True,
                )
                # Don't raise - return None to allow RAG setup to skip gracefully
                return None

        return self._embedding

    def _ensure_local_embedding_metadata(self, model_path: str) -> None:
        """Create optional sentence-transformers metadata locally.

        AIRunner does not allow sentence-transformers to fall back to
        huggingface_hub or any hub cache path for optional metadata files.
        Materialize the small root metadata files locally so the embedding
        model loads entirely from the downloaded directory.
        """
        model_dir = Path(model_path)
        model_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_embedding_metadata_file(
            model_dir / "config_sentence_transformers.json",
            {"__version__": {}},
        )
        self._ensure_embedding_metadata_file(
            model_dir / "README.md",
            "# intfloat/e5-large\n",
        )

    def _ensure_embedding_metadata_file(
        self,
        file_path: Path,
        content: Dict[str, Any] | str,
    ) -> None:
        """Write one optional metadata file when it is absent."""
        if file_path.exists():
            return

        if isinstance(content, dict):
            file_path.write_text(
                json.dumps(content, indent=2) + "\n",
                encoding="utf-8",
            )
            return

        file_path.write_text(content, encoding="utf-8")

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

    def _check_and_download_embedding_model(self, model_path: str) -> bool:
        """Check if embedding model files exist and trigger download if needed.

        Uses llm_file_bootstrap_data.py as the source of truth for required files.

        Args:
            model_path: Path to the embedding model directory

        Returns:
            True if model files exist, False if download was triggered
        """
        from airunner.components.llm.data.bootstrap.llm_file_bootstrap_data import (
            LLM_FILE_BOOTSTRAP_DATA,
        )
        from airunner.enums import SignalCode

        if not hasattr(self, "_embedding_download_pending"):
            self._embedding_download_pending = False
        if not hasattr(self, "_embedding_download_handler_registered"):
            self._embedding_download_handler_registered = False

        # Use llm_file_bootstrap_data as source of truth
        repo_id = _EMBEDDING_REPO_ID

        if repo_id not in LLM_FILE_BOOTSTRAP_DATA:
            self.logger.error(
                f"Embedding model {repo_id} not in LLM_FILE_BOOTSTRAP_DATA"
            )
            return False

        # Check which required files are missing or incomplete
        # files is a dict of {filename: expected_size}
        required_files = LLM_FILE_BOOTSTRAP_DATA[repo_id]["files"]
        missing_files = []

        for required_file, expected_size in required_files.items():
            file_path = os.path.join(model_path, required_file)
            if not os.path.exists(file_path):
                missing_files.append(required_file)
            elif expected_size > 0:
                # Check if file is complete by comparing size
                actual_size = os.path.getsize(file_path)
                if actual_size < expected_size:
                    self.logger.warning(
                        f"File {required_file} is incomplete: {actual_size} bytes vs expected {expected_size} bytes"
                    )
                    missing_files.append(required_file)

        if not missing_files:
            # All files exist
            return True

        # Files are missing - trigger download
        self.logger.info(
            f"Missing {len(missing_files)} files for embedding model {repo_id}, triggering download"
        )
        self.logger.debug(f"Missing files: {missing_files}")

        # Emit signal to trigger download dialog
        # Avoid triggering multiple simultaneous downloads
        if not getattr(self, "_embedding_download_pending", False):
            self._set_embedding_resource_state("loading")
            self.emit_signal(
                SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
                {
                    "repo_id": repo_id,
                    "model_path": model_path,
                    "missing_files": missing_files,
                    "model_type": "embedding",
                },
            )
            self._embedding_download_pending = True

        # Register handler for download completion to retry embedding initialization
        if (
            hasattr(self, "register")
            and not self._embedding_download_handler_registered
        ):
            self.register(
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._on_embedding_download_complete,
            )
            self._embedding_download_handler_registered = True

        return False

    def _on_embedding_download_complete(self, data: dict):
        """Handle embedding model download completion and retry initialization.

        Args:
            data: Download completion data
        """
        repo_id = data.get("repo_id")
        if repo_id == _EMBEDDING_REPO_ID:
            self.logger.info(
                "Embedding model download complete - will initialize on next access"
            )
            # Clear cached embedding so it will be re-initialized on next access
            self._embedding = None
            self._embedding_download_pending = False
            self._set_embedding_resource_state("unloaded")
            # Unregister this handler
            if hasattr(self, "unregister"):
                from airunner.enums import SignalCode

                self.unregister(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._on_embedding_download_complete,
                )
                self._embedding_download_handler_registered = False
