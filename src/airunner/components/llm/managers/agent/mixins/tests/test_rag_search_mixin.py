"""Tests for RAGSearchMixin.

Following red/green/refactor TDD pattern with comprehensive coverage.
"""

from unittest.mock import Mock, patch
from airunner.components.llm.managers.agent.mixins.rag_search_mixin import (
    RAGSearchMixin,
)


class TestableRAGSearchMixin(RAGSearchMixin):
    """Testable version of RAGSearchMixin with required dependencies."""

    def __init__(self):
        self.logger = Mock()
        self._retriever = None
        self.index = None


class TestSearch:
    """Test search method."""

    def test_returns_empty_list_when_no_retriever(self):
        """Should return empty list if retriever is not available."""
        mixin = TestableRAGSearchMixin()
        mixin._retriever = None

        result = mixin.search("test query", k=3)

        assert result == []
        mixin.logger.warning.assert_called()

    def test_performs_search_with_retriever(self):
        """Should perform search using retriever."""
        mixin = TestableRAGSearchMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.QueryBundle"
        ) as mock_qb:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_search_mixin.Document"
            ) as mock_doc:
                mock_retriever = Mock()
                mock_node1 = Mock()
                mock_node1.node.text = "Result 1"
                mock_node1.node.metadata = {"source": "doc1"}
                mock_node2 = Mock()
                mock_node2.node.text = "Result 2"
                mock_node2.node.metadata = {"source": "doc2"}
                mock_retriever.retrieve.return_value = [mock_node1, mock_node2]
                mixin._retriever = mock_retriever

                result = mixin.search("test query", k=3)

                assert len(result) == 2
                mock_qb.assert_called_once_with(query_str="test query")
                mock_retriever.retrieve.assert_called_once()

    def test_limits_results_to_k(self):
        """Should limit results to k parameter."""
        mixin = TestableRAGSearchMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.QueryBundle"
        ):
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_search_mixin.Document"
            ):
                mock_retriever = Mock()
                # Create 5 nodes
                nodes = [Mock() for _ in range(5)]
                for i, node in enumerate(nodes):
                    node.node.text = f"Result {i}"
                    node.node.metadata = {}
                mock_retriever.retrieve.return_value = nodes
                mixin._retriever = mock_retriever

                result = mixin.search("test query", k=2)

                # Should only return 2 results
                assert len(result) == 2

    def test_converts_nodes_to_langchain_documents(self):
        """Should convert LlamaIndex nodes to LangChain Document objects."""
        mixin = TestableRAGSearchMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.QueryBundle"
        ):
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_search_mixin.Document"
            ) as mock_doc_class:
                mock_retriever = Mock()
                mock_node = Mock()
                mock_node.node.text = "Test content"
                mock_node.node.metadata = {"key": "value"}
                mock_retriever.retrieve.return_value = [mock_node]
                mixin._retriever = mock_retriever

                result = mixin.search("test query", k=3)

                mock_doc_class.assert_called_once_with(
                    page_content="Test content", metadata={"key": "value"}
                )

    def test_handles_search_errors(self):
        """Should handle errors during search gracefully."""
        mixin = TestableRAGSearchMixin()

        mock_retriever = Mock()
        mock_retriever.retrieve.side_effect = Exception("Search error")
        mixin._retriever = mock_retriever

        result = mixin.search("test query", k=3)

        assert result == []
        mixin.logger.error.assert_called()

    def test_logs_search_results(self):
        """Should log number of search results returned."""
        mixin = TestableRAGSearchMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.QueryBundle"
        ):
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_search_mixin.Document"
            ):
                mock_retriever = Mock()
                mock_node = Mock()
                mock_node.node.text = "Result"
                mock_node.node.metadata = {}
                mock_retriever.retrieve.return_value = [mock_node]
                mixin._retriever = mock_retriever

                mixin.search("test query", k=3)

                mixin.logger.info.assert_called()


class TestGetRetrieverForQuery:
    """Test get_retriever_for_query method."""

    def test_returns_none_when_no_index(self):
        """Should return None if index is not available."""
        mixin = TestableRAGSearchMixin()
        mixin.index = None

        result = mixin.get_retriever_for_query("test", similarity_top_k=5)

        assert result is None
        mixin.logger.error.assert_called()

    def test_creates_retriever_without_filters(self):
        """Should create retriever without filters when no doc_ids provided."""
        mixin = TestableRAGSearchMixin()
        mixin.index = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.VectorIndexRetriever"
        ) as mock_retriever:
            result = mixin.get_retriever_for_query("test", similarity_top_k=5)

            mock_retriever.assert_called_once_with(
                index=mixin.index, similarity_top_k=5, filters=None
            )
            assert result == mock_retriever.return_value

    def test_creates_retriever_with_doc_id_filters(self):
        """Should create retriever with metadata filters when doc_ids provided."""
        mixin = TestableRAGSearchMixin()
        mixin.index = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.VectorIndexRetriever"
        ) as mock_retriever:
            with patch(
                "airunner.components.llm.managers.agent.mixins.rag_search_mixin.MetadataFilters"
            ) as mock_filters:
                with patch(
                    "airunner.components.llm.managers.agent.mixins.rag_search_mixin.ExactMatchFilter"
                ) as mock_exact:
                    result = mixin.get_retriever_for_query(
                        "test", similarity_top_k=5, doc_ids=["doc1", "doc2"]
                    )

                    # Should create exact match filters for each doc_id
                    assert mock_exact.call_count == 2
                    mock_filters.assert_called_once()

    def test_logs_retriever_creation(self):
        """Should log retriever creation with parameters."""
        mixin = TestableRAGSearchMixin()
        mixin.index = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.VectorIndexRetriever"
        ):
            mixin.get_retriever_for_query(
                "test", similarity_top_k=5, doc_ids=["doc1"]
            )

            mixin.logger.debug.assert_called()

    def test_handles_retriever_creation_errors(self):
        """Should handle errors during retriever creation."""
        mixin = TestableRAGSearchMixin()
        mixin.index = Mock()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.VectorIndexRetriever"
        ) as mock_retriever:
            mock_retriever.side_effect = Exception("Creation error")

            result = mixin.get_retriever_for_query("test", similarity_top_k=5)

            assert result is None
            mixin.logger.error.assert_called()


class TestRetrieverProperty:
    """Test retriever property."""

    def test_creates_multi_index_retriever_first_access(self):
        """Should create MultiIndexRetriever on first access."""
        mixin = TestableRAGSearchMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.MultiIndexRetriever"
        ) as mock_retriever:
            with patch.object(
                mixin, "_get_active_document_ids"
            ) as mock_get_ids:
                mock_get_ids.return_value = ["id1", "id2"]

                result = mixin.retriever

                mock_retriever.assert_called_once_with(
                    rag_mixin=mixin, similarity_top_k=5
                )
                assert result == mock_retriever.return_value

    def test_returns_cached_retriever_subsequent_access(self):
        """Should return cached retriever on subsequent access."""
        mixin = TestableRAGSearchMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.MultiIndexRetriever"
        ) as mock_retriever:
            with patch.object(
                mixin, "_get_active_document_ids"
            ) as mock_get_ids:
                mock_get_ids.return_value = ["id1"]

                first = mixin.retriever
                second = mixin.retriever

                # Should only create once
                assert mock_retriever.call_count == 1
                assert first == second

    def test_logs_active_document_count(self):
        """Should log number of active documents."""
        mixin = TestableRAGSearchMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.MultiIndexRetriever"
        ):
            with patch.object(
                mixin, "_get_active_document_ids"
            ) as mock_get_ids:
                mock_get_ids.return_value = ["id1", "id2", "id3"]

                mixin.retriever

                mixin.logger.debug.assert_called()

    def test_handles_retriever_creation_error(self):
        """Should handle errors during retriever creation."""
        mixin = TestableRAGSearchMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.MultiIndexRetriever"
        ) as mock_retriever:
            with patch.object(
                mixin, "_get_active_document_ids"
            ) as mock_get_ids:
                mock_get_ids.return_value = ["id1"]
                mock_retriever.side_effect = Exception("Creation error")

                result = mixin.retriever

                assert result is None
                mixin.logger.error.assert_called()

    def test_returns_none_when_logger_missing(self):
        """Should handle missing logger gracefully."""
        mixin = TestableRAGSearchMixin()
        delattr(mixin, "logger")

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.MultiIndexRetriever"
        ) as mock_retriever:
            with patch.object(
                mixin, "_get_active_document_ids"
            ) as mock_get_ids:
                mock_get_ids.return_value = ["id1"]
                mock_retriever.side_effect = Exception("Error")

                result = mixin.retriever

                # Should not crash
                assert result is None
