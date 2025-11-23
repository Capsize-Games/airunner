"""Unit tests for RAG unified index search.

These tests verify that the MultiIndexRetriever correctly searches both:
1. Unified in-memory index (from ensure_indexed_files)
2. Per-document persistent indexes (from database documents)
"""

import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest

from llama_index.core import Document as LlamaDocument
from llama_index.core.schema import NodeWithScore, TextNode


class TestUnifiedIndexSearch:
    """Test unified index search in MultiIndexRetriever."""

    def test_retriever_searches_unified_index_when_present(self):
        """Should search unified in-memory index if it exists."""
        from airunner.components.llm.managers.agent.retriever import (
            MultiIndexRetriever,
        )
        from llama_index.core.schema import QueryBundle

        # Create mock RAG mixin with unified index
        mock_rag = Mock()
        mock_rag.logger = Mock()
        mock_rag._get_active_document_ids = Mock(return_value=[])

        # Create a mock unified index with retriever
        mock_index = Mock()
        mock_retriever = Mock()

        # Mock retrieval result with actual node
        test_node = TextNode(text="This is test content from unified index")
        mock_node_with_score = NodeWithScore(node=test_node, score=0.9)
        mock_retriever.retrieve = Mock(return_value=[mock_node_with_score])

        # Patch VectorIndexRetriever creation
        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ) as mock_retriever_class:
            mock_retriever_class.return_value = mock_retriever
            mock_rag._index = mock_index

            # Create retriever and execute search
            retriever = MultiIndexRetriever(mock_rag, similarity_top_k=5)
            query = QueryBundle(query_str="test query")
            results = retriever._retrieve(query)

            # Verify unified index was searched
            assert len(results) == 1
            assert (
                results[0].node.text
                == "This is test content from unified index"
            )
            mock_retriever_class.assert_called_once()

    def test_retriever_skips_unified_index_when_absent(self):
        """Should not error if unified index doesn't exist."""
        from airunner.components.llm.managers.agent.retriever import (
            MultiIndexRetriever,
        )
        from llama_index.core.schema import QueryBundle

        # Create mock RAG mixin WITHOUT unified index
        mock_rag = Mock()
        mock_rag.logger = Mock()
        mock_rag._get_active_document_ids = Mock(return_value=[])
        mock_rag._index = None  # No unified index

        retriever = MultiIndexRetriever(mock_rag, similarity_top_k=5)
        query = QueryBundle(query_str="test query")
        results = retriever._retrieve(query)

        # Should return empty list without error
        assert results == []

    def test_retriever_combines_unified_and_persistent_results(self):
        """Should combine results from both unified and persistent indexes."""
        from airunner.components.llm.managers.agent.retriever import (
            MultiIndexRetriever,
        )
        from llama_index.core.schema import QueryBundle

        # Create mock RAG mixin
        mock_rag = Mock()
        mock_rag.logger = Mock()

        # Mock unified index node
        unified_node = TextNode(text="Content from unified index")
        unified_result = NodeWithScore(node=unified_node, score=0.9)

        # Mock persistent index node
        persistent_node = TextNode(text="Content from persistent index")
        persistent_result = NodeWithScore(node=persistent_node, score=0.8)

        # Mock unified index
        mock_unified_index = Mock()
        mock_rag._index = mock_unified_index

        # Mock persistent index
        mock_persistent_index = Mock()
        mock_rag._get_active_document_ids = Mock(return_value=["doc1"])
        mock_rag._load_doc_index = Mock(return_value=mock_persistent_index)

        # Mock retrievers
        with patch(
            "airunner.components.llm.managers.agent.retriever.VectorIndexRetriever"
        ) as mock_retriever_class:
            # First call returns unified results, second call returns persistent results
            mock_unified_retriever = Mock()
            mock_unified_retriever.retrieve = Mock(
                return_value=[unified_result]
            )

            mock_persistent_retriever = Mock()
            mock_persistent_retriever.retrieve = Mock(
                return_value=[persistent_result]
            )

            mock_retriever_class.side_effect = [
                mock_unified_retriever,
                mock_persistent_retriever,
            ]

            # Execute search
            retriever = MultiIndexRetriever(mock_rag, similarity_top_k=5)
            query = QueryBundle(query_str="test query")
            results = retriever._retrieve(query)

            # Should have both results, sorted by score
            assert len(results) == 2
            assert results[0].score == 0.9  # Unified result (higher score)
            assert results[1].score == 0.8  # Persistent result


class TestRAGContentExtraction:
    """Test RAG content extraction from nodes."""

    def test_search_extracts_text_from_nodes(self):
        """Should extract text content from NodeWithScore objects."""
        from airunner.components.llm.managers.agent.mixins.rag_search_mixin import (
            RAGSearchMixin,
        )
        from llama_index.core.schema import QueryBundle

        # Create test class with mixin
        class TestRAG(RAGSearchMixin):
            def __init__(self):
                self.logger = Mock()
                self._retriever = Mock()

        rag = TestRAG()

        # Create mock nodes with actual text content
        node1 = TextNode(
            text="First test content with real data",
            metadata={"source": "test1"},
        )
        node2 = TextNode(
            text="Second test content with more data",
            metadata={"source": "test2"},
        )

        mock_results = [
            NodeWithScore(node=node1, score=0.9),
            NodeWithScore(node=node2, score=0.8),
        ]

        # Mock retriever to return nodes
        mock_query_bundle = Mock()
        rag._retriever.retrieve = Mock(return_value=mock_results)

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.QueryBundle",
            return_value=mock_query_bundle,
        ):
            results = rag.search("test query", k=5)

        # Verify content extraction
        assert len(results) == 2
        assert results[0].page_content == "First test content with real data"
        assert results[1].page_content == "Second test content with more data"
        assert results[0].metadata == {"source": "test1"}
        assert results[1].metadata == {"source": "test2"}

    def test_search_handles_empty_text_gracefully(self):
        """Should handle nodes with empty or None text."""
        from airunner.components.llm.managers.agent.mixins.rag_search_mixin import (
            RAGSearchMixin,
        )

        class TestRAG(RAGSearchMixin):
            def __init__(self):
                self.logger = Mock()
                self._retriever = Mock()

        rag = TestRAG()

        # Create node with empty text (simulating the bug)
        empty_node = TextNode(text="", metadata={"source": "empty"})
        mock_results = [NodeWithScore(node=empty_node, score=0.9)]

        mock_query_bundle = Mock()
        rag._retriever.retrieve = Mock(return_value=mock_results)

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.QueryBundle",
            return_value=mock_query_bundle,
        ):
            results = rag.search("test query", k=5)

        # Should return document with empty content, not crash
        assert len(results) == 1
        assert results[0].page_content == ""

    def test_search_tries_multiple_text_extraction_methods(self):
        """Should try node.text, get_text(), get_content() for text extraction."""
        from airunner.components.llm.managers.agent.mixins.rag_search_mixin import (
            RAGSearchMixin,
        )

        class TestRAG(RAGSearchMixin):
            def __init__(self):
                self.logger = Mock()
                self._retriever = Mock()

        rag = TestRAG()

        # Create node with text
        node = TextNode(text="Content via .text property")
        mock_results = [NodeWithScore(node=node, score=0.9)]

        mock_query_bundle = Mock()
        rag._retriever.retrieve = Mock(return_value=mock_results)

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_search_mixin.QueryBundle",
            return_value=mock_query_bundle,
        ):
            results = rag.search("test query", k=5)

        # Should successfully extract via .text
        assert results[0].page_content == "Content via .text property"


class TestEnsureIndexedFiles:
    """Test that ensure_indexed_files creates searchable unified index."""

    def test_ensure_indexed_files_creates_unified_index(self):
        """Should create unified index that can be searched."""
        # This would be an integration test requiring actual file I/O
        # Marking as integration test for future implementation
        pytest.skip("Integration test - requires actual LLM setup")

    def test_unified_index_persists_across_searches(self):
        """Unified index should remain available for multiple searches."""
        # This would be an integration test
        pytest.skip("Integration test - requires actual LLM setup")
