"""Tests for MultiIndexRetriever.

Following red/green/refactor TDD pattern with comprehensive coverage.
"""

from unittest.mock import Mock, patch
from airunner.components.llm.managers.agent.retriever import (
    MultiIndexRetriever,
)


class TestMultiIndexRetrieverInit:
    """Test MultiIndexRetriever initialization."""

    def test_stores_rag_mixin_reference(self):
        """Should store reference to rag_mixin."""
        mock_rag = Mock()

        retriever = MultiIndexRetriever(rag_mixin=mock_rag, similarity_top_k=5)

        assert retriever._rag_mixin == mock_rag

    def test_stores_similarity_top_k(self):
        """Should store similarity_top_k parameter."""
        mock_rag = Mock()

        retriever = MultiIndexRetriever(
            rag_mixin=mock_rag, similarity_top_k=10
        )

        assert retriever._similarity_top_k == 10


class TestRetrieve:
    """Test _retrieve method."""

    def test_returns_empty_when_no_active_documents(self):
        """Should return empty list when no active documents."""
        mock_rag = Mock()
        mock_rag._get_active_document_ids.return_value = []
        mock_rag.logger = Mock()

        retriever = MultiIndexRetriever(rag_mixin=mock_rag, similarity_top_k=5)

        with patch(
            "airunner.components.llm.managers.agent.retriever.QueryBundle"
        ) as mock_qb:
            query_bundle = mock_qb.return_value
            result = retriever._retrieve(query_bundle)

        assert result == []
        mock_rag.logger.warning.assert_called()

    def test_loads_and_searches_each_active_document(self):
        """Should load index for each active document and search it."""
        mock_rag = Mock()
        mock_rag._get_active_document_ids.return_value = ["doc1", "doc2"]
        mock_rag.logger = Mock()

        mock_index1 = Mock()
        mock_index2 = Mock()
        mock_rag._load_doc_index.side_effect = [mock_index1, mock_index2]

        retriever = MultiIndexRetriever(rag_mixin=mock_rag, similarity_top_k=5)

        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ) as mock_vec_retriever:
            with patch(
                "airunner.components.llm.managers.agent.retriever.QueryBundle"
            ):
                mock_ret1 = Mock()
                mock_node1 = Mock()
                mock_node1.score = 0.9
                mock_ret1.retrieve.return_value = [mock_node1]

                mock_ret2 = Mock()
                mock_node2 = Mock()
                mock_node2.score = 0.8
                mock_ret2.retrieve.return_value = [mock_node2]

                mock_vec_retriever.side_effect = [mock_ret1, mock_ret2]

                query_bundle = Mock()
                result = retriever._retrieve(query_bundle)

        # Should load both indexes
        assert mock_rag._load_doc_index.call_count == 2
        # Should create retrievers for both
        assert mock_vec_retriever.call_count == 2
        # Should return both nodes
        assert len(result) == 2

    def test_sorts_results_by_score_descending(self):
        """Should sort all results by score (highest first)."""
        mock_rag = Mock()
        mock_rag._get_active_document_ids.return_value = ["doc1", "doc2"]
        mock_rag.logger = Mock()

        mock_index1 = Mock()
        mock_index2 = Mock()
        mock_rag._load_doc_index.side_effect = [mock_index1, mock_index2]

        retriever = MultiIndexRetriever(
            rag_mixin=mock_rag, similarity_top_k=10
        )

        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ) as mock_vec_retriever:
            # Create nodes with different scores
            mock_node1 = Mock()
            mock_node1.score = 0.5
            mock_node2 = Mock()
            mock_node2.score = 0.9
            mock_node3 = Mock()
            mock_node3.score = 0.7

            mock_ret1 = Mock()
            mock_ret1.retrieve.return_value = [mock_node1, mock_node2]
            mock_ret2 = Mock()
            mock_ret2.retrieve.return_value = [mock_node3]

            mock_vec_retriever.side_effect = [mock_ret1, mock_ret2]

            query_bundle = Mock()
            result = retriever._retrieve(query_bundle)

        # Should be sorted: 0.9, 0.7, 0.5
        assert result[0].score == 0.9
        assert result[1].score == 0.7
        assert result[2].score == 0.5

    def test_limits_to_top_k_results(self):
        """Should return only top K results across all indexes."""
        mock_rag = Mock()
        mock_rag._get_active_document_ids.return_value = ["doc1", "doc2"]
        mock_rag.logger = Mock()

        mock_rag._load_doc_index.return_value = Mock()

        retriever = MultiIndexRetriever(rag_mixin=mock_rag, similarity_top_k=2)

        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ) as mock_vec_retriever:
            # Create 5 nodes total
            nodes = [Mock() for _ in range(5)]
            for i, node in enumerate(nodes):
                node.score = 0.9 - (i * 0.1)

            mock_ret1 = Mock()
            mock_ret1.retrieve.return_value = nodes[:3]
            mock_ret2 = Mock()
            mock_ret2.retrieve.return_value = nodes[3:]

            mock_vec_retriever.side_effect = [mock_ret1, mock_ret2]

            query_bundle = Mock()
            result = retriever._retrieve(query_bundle)

        # Should only return top 2
        assert len(result) == 2

    def test_skips_documents_with_failed_index_load(self):
        """Should skip documents where index loading fails."""
        mock_rag = Mock()
        mock_rag._get_active_document_ids.return_value = ["doc1", "doc2"]
        mock_rag.logger = Mock()

        # First fails, second succeeds
        mock_index = Mock()
        mock_rag._load_doc_index.side_effect = [None, mock_index]

        retriever = MultiIndexRetriever(rag_mixin=mock_rag, similarity_top_k=5)

        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ) as mock_vec_retriever:
            mock_ret = Mock()
            mock_node = Mock()
            mock_node.score = 0.8
            mock_ret.retrieve.return_value = [mock_node]
            mock_vec_retriever.return_value = mock_ret

            query_bundle = Mock()
            result = retriever._retrieve(query_bundle)

        # Should only create retriever once (for successful load)
        assert mock_vec_retriever.call_count == 1
        assert len(result) == 1

    def test_continues_on_retrieval_error(self):
        """Should log error and continue with other indexes if retrieval fails."""
        mock_rag = Mock()
        mock_rag._get_active_document_ids.return_value = ["doc1", "doc2"]
        mock_rag.logger = Mock()

        mock_rag._load_doc_index.return_value = Mock()

        retriever = MultiIndexRetriever(rag_mixin=mock_rag, similarity_top_k=5)

        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ) as mock_vec_retriever:
            # First retriever raises error, second succeeds
            mock_ret1 = Mock()
            mock_ret1.retrieve.side_effect = Exception("Retrieval error")

            mock_ret2 = Mock()
            mock_node = Mock()
            mock_node.score = 0.8
            mock_ret2.retrieve.return_value = [mock_node]

            mock_vec_retriever.side_effect = [mock_ret1, mock_ret2]

            query_bundle = Mock()
            result = retriever._retrieve(query_bundle)

        # Should log error
        mock_rag.logger.error.assert_called()
        # Should still return result from second index
        assert len(result) == 1

    def test_logs_search_info(self):
        """Should log information about search."""
        mock_rag = Mock()
        mock_rag._get_active_document_ids.return_value = ["doc1"]
        mock_rag.logger = Mock()
        mock_rag._load_doc_index.return_value = Mock()

        retriever = MultiIndexRetriever(rag_mixin=mock_rag, similarity_top_k=5)

        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ):
            query_bundle = Mock()
            retriever._retrieve(query_bundle)

        mock_rag.logger.info.assert_called()

    def test_handles_none_scores_gracefully(self):
        """Should handle nodes with None scores when sorting."""
        mock_rag = Mock()
        mock_rag._get_active_document_ids.return_value = ["doc1"]
        mock_rag.logger = Mock()
        mock_rag._load_doc_index.return_value = Mock()

        retriever = MultiIndexRetriever(rag_mixin=mock_rag, similarity_top_k=5)

        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ) as mock_vec_retriever:
            # Create nodes with None scores
            mock_node1 = Mock()
            mock_node1.score = None
            mock_node2 = Mock()
            mock_node2.score = 0.8

            mock_ret = Mock()
            mock_ret.retrieve.return_value = [mock_node1, mock_node2]
            mock_vec_retriever.return_value = mock_ret

            query_bundle = Mock()
            result = retriever._retrieve(query_bundle)

        # Should not crash, should treat None as 0.0
        assert len(result) == 2
        # Node with 0.8 score should be first
        assert result[0].score == 0.8
