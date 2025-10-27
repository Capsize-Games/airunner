"""Tests for RAGLifecycleMixin.

Following red/green/refactor TDD pattern with comprehensive coverage.
"""

import gc
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin import (
    RAGLifecycleMixin,
)


class TestableRAGLifecycleMixin(RAGLifecycleMixin):
    """Testable version of RAGLifecycleMixin - override __init__ to avoid dependencies."""

    def __init__(self):
        # Don't call super().__init__() to avoid setup
        self.logger = Mock()
        self._document_reader = None
        self._index = None
        self._retriever = None
        self._embedding = None
        self._rag_engine = None
        self._rag_engine_tool = None
        self._text_splitter = None
        self._target_files = None
        self._doc_metadata_cache = {}
        self._cache_validated = False
        self._index_registry = None
        self._doc_indexes_cache = {}
        self._loaded_doc_ids = []


class TestInit:
    """Test __init__ method."""

    def test_initializes_all_state_variables(self):
        """Should initialize all RAG state variables to None/empty."""
        with patch.object(RAGLifecycleMixin, "_setup_rag"):
            mixin = RAGLifecycleMixin()

        assert mixin._document_reader is None
        assert mixin._index is None
        assert mixin._retriever is None
        assert mixin._embedding is None
        assert mixin._text_splitter is None
        assert mixin._target_files is None
        assert isinstance(mixin._doc_metadata_cache, dict)
        assert mixin._cache_validated is False

    def test_initializes_per_document_architecture(self):
        """Should initialize per-document index architecture."""
        with patch.object(RAGLifecycleMixin, "_setup_rag"):
            mixin = RAGLifecycleMixin()

        assert mixin._index_registry is None
        assert isinstance(mixin._doc_indexes_cache, dict)
        assert isinstance(mixin._loaded_doc_ids, list)

    def test_calls_setup_rag(self):
        """Should call _setup_rag during initialization."""
        with patch.object(RAGLifecycleMixin, "_setup_rag") as mock_setup:
            mixin = RAGLifecycleMixin()

        mock_setup.assert_called_once()


class TestSetupRag:
    """Test _setup_rag method."""

    def test_skips_setup_when_skip_agent_load_true(self):
        """Should skip setup if _skip_agent_load flag is set."""
        mixin = TestableRAGLifecycleMixin()
        mixin._skip_agent_load = True

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Settings"
        ):
            mixin._setup_rag()

        mixin.logger.debug.assert_called()

    def test_defers_setup_when_embedding_unavailable(self):
        """Should defer setup if embedding property not available."""
        mixin = TestableRAGLifecycleMixin()
        # Don't set embedding attribute

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Settings"
        ):
            mixin._setup_rag()

        mixin.logger.debug.assert_called()

    def test_configures_llamaindex_settings(self):
        """Should configure LlamaIndex Settings with embedding and text_splitter."""
        mixin = TestableRAGLifecycleMixin()
        mixin.embedding = Mock()
        mixin.text_splitter = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Settings"
        ) as mock_settings:
            with patch.object(mixin, "_detect_and_migrate_old_index"):
                mixin._setup_rag()

        assert mock_settings.embed_model == mixin.embedding
        assert mock_settings.node_parser == mixin.text_splitter

    def test_checks_for_old_index_migration(self):
        """Should check for and migrate old unified index."""
        mixin = TestableRAGLifecycleMixin()
        mixin.embedding = Mock()
        mixin.text_splitter = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Settings"
        ):
            with patch.object(
                mixin, "_detect_and_migrate_old_index"
            ) as mock_migrate:
                mixin._setup_rag()

        mock_migrate.assert_called_once()

    def test_logs_success(self):
        """Should log successful initialization."""
        mixin = TestableRAGLifecycleMixin()
        mixin.embedding = Mock()
        mixin.text_splitter = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Settings"
        ):
            with patch.object(mixin, "_detect_and_migrate_old_index"):
                mixin._setup_rag()

        mixin.logger.info.assert_called()

    def test_handles_setup_errors(self):
        """Should handle and log errors during setup."""
        mixin = TestableRAGLifecycleMixin()
        mixin.embedding = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Settings"
        ) as mock_settings:
            mock_settings.embed_model = Mock(
                side_effect=Exception("Setup error")
            )

            mixin._setup_rag()

        mixin.logger.error.assert_called()


class TestReloadRag:
    """Test reload_rag method."""

    def test_clears_all_component_references(self):
        """Should clear all RAG component references."""
        mixin = TestableRAGLifecycleMixin()
        mixin._index = Mock()
        mixin._retriever = Mock()
        mixin._rag_engine = Mock()
        mixin._document_reader = Mock()

        mixin.reload_rag()

        assert mixin._index is None
        assert mixin._retriever is None
        assert mixin._rag_engine is None
        assert mixin._document_reader is None

    def test_clears_all_caches(self):
        """Should clear all cache dictionaries."""
        mixin = TestableRAGLifecycleMixin()
        mixin._doc_metadata_cache = {"key": "value"}
        mixin._doc_indexes_cache = {"doc1": Mock()}
        mixin._loaded_doc_ids = ["id1", "id2"]
        mixin._cache_validated = True

        mixin.reload_rag()

        assert len(mixin._doc_metadata_cache) == 0
        assert len(mixin._doc_indexes_cache) == 0
        assert len(mixin._loaded_doc_ids) == 0
        assert mixin._cache_validated is False

    def test_resets_index_registry(self):
        """Should reset index registry to None."""
        mixin = TestableRAGLifecycleMixin()
        mixin._index_registry = {"registry": "data"}

        mixin.reload_rag()

        assert mixin._index_registry is None

    def test_logs_reload(self):
        """Should log reload operation."""
        mixin = TestableRAGLifecycleMixin()

        mixin.reload_rag()

        mixin.logger.debug.assert_called()


class TestClearRagDocuments:
    """Test clear_rag_documents method."""

    def test_clears_target_files(self):
        """Should clear target_files."""
        mixin = TestableRAGLifecycleMixin()
        mixin.target_files = ["file1.txt", "file2.txt"]

        with patch.object(mixin, "reload_rag"):
            mixin.clear_rag_documents()

        assert mixin.target_files is None

    def test_calls_reload_rag(self):
        """Should call reload_rag after clearing files."""
        mixin = TestableRAGLifecycleMixin()

        with patch.object(mixin, "reload_rag") as mock_reload:
            mixin.clear_rag_documents()

        mock_reload.assert_called_once()

    def test_skips_reload_when_unloading(self):
        """Should not reload if currently unloading."""
        mixin = TestableRAGLifecycleMixin()
        mixin._is_unloading = True

        with patch.object(mixin, "reload_rag") as mock_reload:
            mixin.clear_rag_documents()

        mock_reload.assert_not_called()

    def test_logs_clear(self):
        """Should log clear operation."""
        mixin = TestableRAGLifecycleMixin()

        with patch.object(mixin, "reload_rag"):
            mixin.clear_rag_documents()

        mixin.logger.debug.assert_called()


class TestUnloadRag:
    """Test unload_rag method."""

    def test_clears_target_files(self):
        """Should clear target files."""
        mixin = TestableRAGLifecycleMixin()
        mixin.target_files = ["file1.txt"]

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.gc"
        ):
            mixin.unload_rag()

        assert mixin.target_files is None

    def test_deletes_embedding_model(self):
        """Should delete embedding model and internal attributes."""
        mixin = TestableRAGLifecycleMixin()
        mock_embed = Mock()
        mock_embed._model = Mock()
        mock_embed.model = Mock()
        mixin._embedding = mock_embed

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.gc"
        ):
            mixin.unload_rag()

        assert mixin._embedding is None

    def test_handles_embedding_deletion_errors(self):
        """Should handle errors during embedding deletion gracefully."""
        mixin = TestableRAGLifecycleMixin()
        mock_embed = Mock()
        # Make _model raise error on deletion
        type(mock_embed).model = property(
            lambda self: None,
            lambda self, v: (_ for _ in ()).throw(Exception("Delete error")),
        )
        mixin._embedding = mock_embed

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.gc"
        ):
            mixin.unload_rag()

        mixin.logger.warning.assert_called()

    def test_clears_text_splitter(self):
        """Should clear text splitter."""
        mixin = TestableRAGLifecycleMixin()
        mixin._text_splitter = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.gc"
        ):
            mixin.unload_rag()

        assert mixin._text_splitter is None

    def test_triggers_garbage_collection(self):
        """Should trigger garbage collection."""
        mixin = TestableRAGLifecycleMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.gc"
        ) as mock_gc:
            mixin.unload_rag()

        mock_gc.collect.assert_called_once()

    def test_sets_and_unsets_unloading_flag(self):
        """Should set _is_unloading flag during operation."""
        mixin = TestableRAGLifecycleMixin()

        flag_states = []

        def track_flag(*args, **kwargs):
            flag_states.append(getattr(mixin, "_is_unloading", None))

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.gc"
        ) as mock_gc:
            mock_gc.collect.side_effect = track_flag
            mixin.unload_rag()

        # Flag should be True during execution
        assert True in flag_states
        # Flag should be False after completion
        assert mixin._is_unloading is False

    def test_logs_unload(self):
        """Should log unload operation."""
        mixin = TestableRAGLifecycleMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.gc"
        ):
            mixin.unload_rag()

        mixin.logger.debug.assert_called()


class TestLoadHtmlIntoRag:
    """Test load_html_into_rag method."""

    def test_parses_html_and_extracts_text(self):
        """Should parse HTML and extract text content."""
        mixin = TestableRAGLifecycleMixin()
        mixin._index = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.BeautifulSoup"
        ) as mock_soup:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Document"
            ) as mock_doc:
                with patch.object(mixin, "_generate_doc_id") as mock_gen_id:
                    mock_gen_id.return_value = "test_id"
                    mock_soup_instance = Mock()
                    mock_soup_instance.get_text.return_value = "Extracted text"
                    mock_soup.return_value = mock_soup_instance

                    mixin.load_html_into_rag(
                        "<html><body>Test</body></html>", "test_source"
                    )

                    mock_soup.assert_called_once_with(
                        "<html><body>Test</body></html>", "html.parser"
                    )
                    mock_soup_instance.get_text.assert_called_once_with(
                        separator="\n", strip=True
                    )

    def test_creates_document_with_metadata(self):
        """Should create Document with proper metadata."""
        mixin = TestableRAGLifecycleMixin()
        mixin._index = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.BeautifulSoup"
        ) as mock_soup:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Document"
            ) as mock_doc:
                with patch.object(mixin, "_generate_doc_id") as mock_gen_id:
                    mock_gen_id.return_value = "test_id"
                    mock_soup_instance = Mock()
                    mock_soup_instance.get_text.return_value = "Text"
                    mock_soup.return_value = mock_soup_instance

                    mixin.load_html_into_rag("<html>Test</html>", "my_source")

                    mock_doc.assert_called_once_with(
                        text="Text",
                        metadata={
                            "source": "my_source",
                            "doc_id": "test_id",
                            "file_type": ".html",
                        },
                    )

    def test_inserts_document_into_index(self):
        """Should insert document into existing index."""
        mixin = TestableRAGLifecycleMixin()
        mock_index = Mock()
        mixin._index = mock_index

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.BeautifulSoup"
        ):
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Document"
            ) as mock_doc:
                with patch.object(mixin, "_generate_doc_id"):
                    mock_doc_instance = Mock()
                    mock_doc.return_value = mock_doc_instance

                    mixin.load_html_into_rag("<html>Test</html>")

                    mock_index.insert.assert_called_once_with(
                        mock_doc_instance
                    )

    def test_warns_when_no_index_available(self):
        """Should warn when index is not available."""
        mixin = TestableRAGLifecycleMixin()
        mixin._index = None

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.BeautifulSoup"
        ):
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Document"
            ):
                with patch.object(mixin, "_generate_doc_id"):
                    mixin.load_html_into_rag("<html>Test</html>")

                    mixin.logger.warning.assert_called()

    def test_handles_html_parsing_errors(self):
        """Should handle errors during HTML parsing."""
        mixin = TestableRAGLifecycleMixin()
        mixin._index = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.BeautifulSoup"
        ) as mock_soup:
            mock_soup.side_effect = Exception("Parse error")

            mixin.load_html_into_rag("<html>Test</html>")

            mixin.logger.error.assert_called()

    def test_logs_successful_insert(self):
        """Should log successful HTML content insertion."""
        mixin = TestableRAGLifecycleMixin()
        mixin._index = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.BeautifulSoup"
        ):
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_lifecycle_mixin.Document"
            ):
                with patch.object(mixin, "_generate_doc_id"):
                    mixin.load_html_into_rag(
                        "<html>Test</html>", "test_source"
                    )

                    mixin.logger.info.assert_called()
