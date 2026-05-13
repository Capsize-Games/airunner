"""Unit tests for LangChain-native RAG search."""

from unittest.mock import Mock

import pytest
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from airunner.components.llm.managers.agent.vector_index import (
    DocumentVectorIndex,
)


class FakeEmbeddings:
    """Deterministic embedding stub for unit tests."""

    def embed_documents(self, texts):
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        return self._vector(text)

    def _vector(self, text):
        lowered = text.lower()
        return [
            float("alpha" in lowered),
            float("beta" in lowered),
            float("gamma" in lowered),
        ]


class TestUnifiedIndexSearch:
    """Test unified index search in MultiIndexRetriever."""

    def test_retriever_searches_unified_index_when_present(self):
        """Should search unified in-memory index if it exists."""
        from airunner.components.llm.managers.agent.retriever import (
            MultiIndexRetriever,
        )

        embeddings = FakeEmbeddings()
        mock_rag = Mock()
        mock_rag.logger = Mock()
        mock_rag._get_active_document_ids = Mock(return_value=[])
        mock_rag.embedding = embeddings
        mock_rag._index = DocumentVectorIndex.from_documents(
            [Document(page_content="alpha content from unified index")],
            embeddings,
            RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=0),
        )

        retriever = MultiIndexRetriever(mock_rag, similarity_top_k=5)
        results = retriever.retrieve("alpha")

        assert len(results) == 1
        assert "unified index" in results[0].page_content

    def test_retriever_skips_unified_index_when_absent(self):
        """Should not error if unified index doesn't exist."""
        from airunner.components.llm.managers.agent.retriever import (
            MultiIndexRetriever,
        )

        mock_rag = Mock()
        mock_rag.logger = Mock()
        mock_rag.embedding = FakeEmbeddings()
        mock_rag._get_active_document_ids = Mock(return_value=[])
        mock_rag._index = None

        retriever = MultiIndexRetriever(mock_rag, similarity_top_k=5)
        results = retriever.retrieve("alpha")

        assert results == []

    def test_retriever_combines_unified_and_persistent_results(self):
        """Should combine results from both unified and persistent indexes."""
        from airunner.components.llm.managers.agent.retriever import (
            MultiIndexRetriever,
        )

        embeddings = FakeEmbeddings()
        mock_rag = Mock()
        mock_rag.logger = Mock()
        mock_rag.embedding = embeddings
        mock_rag._index = DocumentVectorIndex.from_documents(
            [Document(page_content="alpha content from unified index")],
            embeddings,
            RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=0),
        )
        mock_persistent_index = Mock()
        mock_persistent_index.similarity_search_by_vector.return_value = [
            Mock(document=Document(page_content="beta content"), score=0.5)
        ]
        mock_rag._get_active_document_ids = Mock(return_value=["doc1"])
        mock_rag._load_doc_index = Mock(return_value=mock_persistent_index)

        retriever = MultiIndexRetriever(mock_rag, similarity_top_k=5)
        results = retriever.retrieve("alpha beta")

        assert len(results) == 2
        assert results[0].page_content
        assert results[1].page_content


class TestRAGContentExtraction:
    """Test RAG content extraction from nodes."""

    def test_search_returns_documents_from_retriever(self):
        """Should return LangChain documents from the retriever."""
        from airunner.components.llm.managers.agent.mixins.rag_search_mixin import (
            RAGSearchMixin,
        )

        class TestRAG(RAGSearchMixin):
            def __init__(self):
                self.logger = Mock()
                self._retriever = Mock()

        rag = TestRAG()
        rag._retriever.retrieve = Mock(
            return_value=[
                Document(
                    page_content="First test content with real data",
                    metadata={"source": "test1"},
                ),
                Document(
                    page_content="Second test content with more data",
                    metadata={"source": "test2"},
                ),
            ]
        )

        results = rag.search("test query", k=5)

        assert len(results) == 2
        assert results[0].page_content == "First test content with real data"
        assert results[1].page_content == "Second test content with more data"
        assert results[0].metadata == {"source": "test1"}
        assert results[1].metadata == {"source": "test2"}

    def test_search_handles_empty_text_gracefully(self):
        """Should handle empty document content without crashing."""
        from airunner.components.llm.managers.agent.mixins.rag_search_mixin import (
            RAGSearchMixin,
        )

        class TestRAG(RAGSearchMixin):
            def __init__(self):
                self.logger = Mock()
                self._retriever = Mock()

        rag = TestRAG()
        rag._retriever.retrieve = Mock(
            return_value=[Document(page_content="", metadata={"source": "empty"})]
        )

        results = rag.search("test query", k=5)

        assert len(results) == 1
        assert results[0].page_content == ""

    def test_vector_index_persists_and_loads(self, tmp_path):
        """Persisted indexes should remain searchable after reload."""
        embeddings = FakeEmbeddings()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=100,
            chunk_overlap=0,
        )
        index = DocumentVectorIndex.from_documents(
            [Document(page_content="alpha content for persistence")],
            embeddings,
            splitter,
        )

        persist_dir = tmp_path / "persisted-index"
        index.persist(str(persist_dir))

        loaded = DocumentVectorIndex.load(str(persist_dir))
        results = loaded.similarity_search("alpha", embeddings, 1)

        assert len(results) == 1
        assert "alpha content" in results[0].document.page_content


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
