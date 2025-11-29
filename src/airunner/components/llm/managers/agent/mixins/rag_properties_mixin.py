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
            # Get RAG settings with safe defaults
            rag_settings = getattr(self, "rag_settings", None)
            chunk_size = 512  # default
            chunk_overlap = 50  # default

            if rag_settings is not None:
                chunk_size = getattr(rag_settings, "chunk_size", 512)
                chunk_overlap = getattr(rag_settings, "chunk_overlap", 50)

            self._text_splitter = SentenceSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
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

                # Check if model files exist and trigger download if needed
                if not self._check_and_download_embedding_model(model_name):
                    self.logger.warning(
                        "Embedding model files missing - download in progress"
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

                # Set quantization flag if using CPU or limited GPU memory
                # This can reduce memory usage significantly
                # quantization_flag = device == "cpu"

                # Use fp16 to reduce VRAM usage (~650MB vs ~1.3GB)
                model_kwargs = {}
                if device == "cuda":
                    model_kwargs["torch_dtype"] = torch.float16

                self._embedding = HuggingFaceEmbedding(
                    model_name=model_name,
                    device=device,
                    trust_remote_code=True,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                    model_kwargs=model_kwargs,
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
        storage_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "rag",
            "storage",
        )
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir

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
        repo_id = "intfloat/e5-large"

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
        if repo_id == "intfloat/e5-large":
            self.logger.info(
                "Embedding model download complete - will initialize on next access"
            )
            # Clear cached embedding so it will be re-initialized on next access
            self._embedding = None
            self._embedding_download_pending = False
            # Unregister this handler
            if hasattr(self, "unregister"):
                from airunner.enums import SignalCode

                self.unregister(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._on_embedding_download_complete,
                )
                self._embedding_download_handler_registered = False
