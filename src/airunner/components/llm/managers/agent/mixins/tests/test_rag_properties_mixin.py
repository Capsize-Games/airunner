"""Tests for RAGPropertiesMixin.

Following red/green/refactor TDD pattern with comprehensive coverage.
"""

import os
from unittest.mock import Mock, patch
from airunner.components.llm.managers.agent.mixins.rag_properties_mixin import (
    RAGPropertiesMixin,
)


class TestableRAGPropertiesMixin(RAGPropertiesMixin):
    """Testable version of RAGPropertiesMixin with required dependencies."""

    def __init__(self):
        self.logger = Mock()
        self.path_settings = Mock()
        self.path_settings.base_path = "/test/base"
        self.knowledge_settings = Mock()
        self.knowledge_settings.chunk_size = 512
        self.knowledge_settings.chunk_overlap = 50
        self.system_prompt = "Test system prompt"
        self.botname = "TestBot"
        self._text_splitter = None
        self._index_registry = None
        self._embedding = None
        self._target_files = None

    def _load_registry(self):
        """Mock implementation of _load_registry from RAGIndexManagementMixin."""
        return {"documents": {}, "version": "1.0"}

    def _get_active_document_names(self):
        """Mock implementation of _get_active_document_names from RAGDocumentMixin."""
        return []


class TestTextSplitter:
    """Test text_splitter property."""

    def test_creates_sentence_splitter_first_access(self):
        """Should create SentenceSplitter on first access."""
        mixin = TestableRAGPropertiesMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.SentenceSplitter"
        ) as mock_splitter:
            result = mixin.text_splitter

            mock_splitter.assert_called_once_with(
                chunk_size=512, chunk_overlap=50
            )
            assert result == mock_splitter.return_value

    def test_returns_cached_splitter_subsequent_access(self):
        """Should return cached splitter on subsequent access."""
        mixin = TestableRAGPropertiesMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.SentenceSplitter"
        ) as mock_splitter:
            first = mixin.text_splitter
            second = mixin.text_splitter

            # Should only create once
            assert mock_splitter.call_count == 1
            assert first == second


class TestDocIndexesDir:
    """Test doc_indexes_dir property."""

    def test_returns_per_document_indexes_path(self):
        """Should return path to per-document indexes directory."""
        mixin = TestableRAGPropertiesMixin()

        with patch("os.makedirs"):
            result = mixin.doc_indexes_dir

        expected = os.path.expanduser("/test/base/rag/doc_indexes")
        assert result == expected


class TestRegistryPath:
    """Test registry_path property."""

    def test_returns_registry_json_path(self):
        """Should return path to document registry JSON file."""
        mixin = TestableRAGPropertiesMixin()

        with patch("os.makedirs"):
            result = mixin.registry_path

        expected = os.path.expanduser(
            "/test/base/rag/doc_indexes/index_registry.json"
        )
        assert result == expected
        assert result == expected


class TestIndexRegistry:
    """Test index_registry property."""

    def test_loads_registry_first_access(self):
        """Should load registry from disk on first access."""
        mixin = TestableRAGPropertiesMixin()

        with patch.object(mixin, "_load_registry") as mock_load:
            mock_load.return_value = {"test": "data"}

            result = mixin.index_registry

            mock_load.assert_called_once()
            assert result == {"test": "data"}

    def test_returns_cached_registry_subsequent_access(self):
        """Should return cached registry on subsequent access."""
        mixin = TestableRAGPropertiesMixin()

        with patch.object(mixin, "_load_registry") as mock_load:
            mock_load.return_value = {"test": "data"}

            first = mixin.index_registry
            second = mixin.index_registry

            # Should only load once
            assert mock_load.call_count == 1
            assert first == second


class TestEmbedding:
    """Test embedding property."""

    def test_uses_local_path_not_huggingface_repo_id(self):
        """CRITICAL: Should use local filesystem path, not HuggingFace repo ID.

        Bug: Previously used 'intfloat/e5-large' directly, which tried to
        download from HuggingFace even when model files existed locally.
        Fix: Must construct path: {base_path}/text/models/llm/embedding/intfloat/e5-large
        """
        mixin = TestableRAGPropertiesMixin()
        mixin.path_settings.base_path = "/test/airunner/base"

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.HuggingFaceEmbedding"
        ) as mock_embed:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.torch"
            ) as mock_torch:
                with patch(
                    "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.AIRUNNER_LOCAL_FILES_ONLY",
                    True,
                ):
                    mock_torch.cuda.is_available.return_value = True

                    result = mixin.embedding

                    # Should be called with LOCAL PATH, not repo ID
                    expected_path = os.path.expanduser(
                        "/test/airunner/base/text/models/llm/embedding/intfloat/e5-large"
                    )
                    mock_embed.assert_called_once()
                    call_kwargs = mock_embed.call_args[1]
                    assert call_kwargs["model_name"] == expected_path
                    assert call_kwargs["local_files_only"] is True
                    assert result == mock_embed.return_value

    def test_creates_embedding_model_first_access(self):
        """Should create HuggingFaceEmbedding on first access."""
        mixin = TestableRAGPropertiesMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.HuggingFaceEmbedding"
        ) as mock_embed:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.torch"
            ) as mock_torch:
                with patch(
                    "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.AIRUNNER_LOCAL_FILES_ONLY",
                    False,
                ):
                    mock_torch.cuda.is_available.return_value = True

                    result = mixin.embedding

                    # When not local_files_only, verify device is set correctly
                    mock_embed.assert_called_once()
                    call_kwargs = mock_embed.call_args[1]
                    assert call_kwargs["device"] == "cuda"
                    assert result == mock_embed.return_value

    def test_uses_cpu_when_cuda_unavailable(self):
        """Should use CPU device when CUDA is not available."""
        mixin = TestableRAGPropertiesMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.HuggingFaceEmbedding"
        ) as mock_embed:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.torch"
            ) as mock_torch:
                with patch(
                    "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.AIRUNNER_LOCAL_FILES_ONLY",
                    False,
                ):
                    mock_torch.cuda.is_available.return_value = False
                    # Mock MPS to also be unavailable
                    mock_torch.backends.mps.is_available.return_value = False

                    mixin.embedding

                    mock_embed.assert_called_once()
                    call_kwargs = mock_embed.call_args[1]
                    assert call_kwargs["device"] == "cpu"

    def test_returns_cached_embedding_subsequent_access(self):
        """Should return cached embedding on subsequent access."""
        mixin = TestableRAGPropertiesMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.HuggingFaceEmbedding"
        ) as mock_embed:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.torch"
            ) as mock_torch:
                with patch(
                    "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.AIRUNNER_LOCAL_FILES_ONLY",
                    False,
                ):
                    mock_torch.cuda.is_available.return_value = True

                    first = mixin.embedding
                    second = mixin.embedding

                    # Should only create once
                    assert mock_embed.call_count == 1
                    assert first == second

    def test_logs_error_on_embedding_creation_failure(self):
        """Should log error and return None if embedding creation fails."""
        mixin = TestableRAGPropertiesMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.HuggingFaceEmbedding"
        ) as mock_embed:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.torch"
            ) as mock_torch:
                with patch(
                    "airunner.components.llm.managers.agent.mixins.rag_properties_mixin.AIRUNNER_LOCAL_FILES_ONLY",
                    False,
                ):
                    mock_torch.cuda.is_available.return_value = True
                    mock_embed.side_effect = Exception("Test error")

                result = mixin.embedding

                mixin.logger.error.assert_called()
                assert result is None


class TestTargetFiles:
    """Test target_files getter and setter."""

    def test_getter_returns_current_value(self):
        """Should return current target_files value."""
        mixin = TestableRAGPropertiesMixin()
        mixin._target_files = ["file1.txt", "file2.txt"]

        result = mixin.target_files

        assert result == ["file1.txt", "file2.txt"]

    def test_setter_updates_value(self):
        """Should update target_files value."""
        mixin = TestableRAGPropertiesMixin()

        mixin.target_files = ["new1.txt", "new2.txt"]

        assert mixin._target_files == ["new1.txt", "new2.txt"]

    def test_setter_accepts_none(self):
        """Should accept None to clear target files."""
        mixin = TestableRAGPropertiesMixin()
        mixin._target_files = ["file1.txt"]

        mixin.target_files = None

        assert mixin._target_files is None


class TestRagSystemPrompt:
    """Test rag_system_prompt property."""

    def test_returns_rag_system_prompt(self):
        """Should return RAG system prompt for document-based assistance."""
        mixin = TestableRAGPropertiesMixin()

        result = mixin.rag_system_prompt

        # Verify key components of the RAG system prompt
        assert "helpful AI assistant" in result
        assert "document database" in result
        assert "context from the documents" in result
        assert "cite the document sources" in result


class TestStoragePersistDir:
    """Test storage_persist_dir property."""

    def test_returns_legacy_unified_index_path(self):
        """Should return path to legacy unified index directory."""
        mixin = TestableRAGPropertiesMixin()

        with patch("os.makedirs"):
            result = mixin.storage_persist_dir

        expected = os.path.expanduser("/test/base/rag/storage")
        assert result == expected

    def test_creates_directory_if_not_exists(self):
        """Should create directory if it doesn't exist."""
        mixin = TestableRAGPropertiesMixin()

        with patch("os.makedirs") as mock_makedirs:
            mixin.storage_persist_dir

            mock_makedirs.assert_called_once()
