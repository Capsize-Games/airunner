"""
Test for RAGMixin index property: covers index refresh logic when new documents are present.
Mocks all model/external dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.handlers.llm.agent.rag_mixin import RAGMixin


@pytest.fixture
def rag_mixin_with_mocks():
    # Create a real RAGMixin instance
    rag = RAGMixin.__new__(RAGMixin)
    rag.logger = MagicMock()
    rag._RAGMixin__keyword_cache = {}
    rag._RAGMixin__last_index_refresh = 0
    rag._RAGMixin__index = None
    rag.storage_context = object()  # Use a simple object, not a MagicMock
    rag._load_index_from_documents = MagicMock()  # Patch to do nothing
    rag._save_index_to_disc = MagicMock()
    rag.text_splitter = MagicMock()
    return rag


def test_index_refresh_adds_new_nodes(monkeypatch, rag_mixin_with_mocks):
    rag = rag_mixin_with_mocks
    # Simulate an index with one doc, and a new doc to add
    mock_index = MagicMock()
    # Set up docstore and index_struct.table as dicts for keyword updates
    mock_index.docstore.docs = {"doc1": MagicMock()}
    mock_index.index_struct.table = {}
    mock_index.docstore.add_documents = MagicMock()
    # Patch load_index_from_storage to return our mock_index
    monkeypatch.setattr(
        "airunner.handlers.llm.agent.rag_mixin.load_index_from_storage",
        lambda storage_context: mock_index,
    )
    rag._RAGMixin__index = None  # Force reload from storage
    rag._RAGMixin__last_index_refresh = 0
    # Patch the documents property to return two docs (one new)
    doc1 = MagicMock()
    doc1.doc_id = "doc1"
    doc2 = MagicMock()
    doc2.doc_id = "doc2"
    with patch.object(
        RAGMixin, "documents", new_callable=PropertyMock
    ) as mock_docs:
        mock_docs.return_value = [doc1, doc2]
        # text_splitter returns a node for doc2
        mock_node = MagicMock()
        mock_node.text = "doc2 text"
        mock_node.node_id = "node2"
        rag.text_splitter.get_nodes_from_documents.side_effect = lambda docs: (
            [mock_node]
            if docs and getattr(docs[0], "doc_id", None) == "doc2"
            else []
        )
        # Patch _extract_keywords_from_text to return a keyword
        monkeypatch.setattr(
            RAGMixin,
            "_extract_keywords_from_text",
            staticmethod(lambda text: {"kw"}),
        )
        # Patch time to force refresh
        with patch("time.time", return_value=1000):
            rag._RAGMixin__last_index_refresh = 0
            rag._RAGMixin__index = None  # Force reload from storage
            result = RAGMixin.index.fget(rag)
    # Debug output
    print(
        "add_documents call args:", mock_index.docstore.add_documents.call_args
    )
    print("index_struct.table:", mock_index.index_struct.table)
    # Should add new node to docstore
    mock_index.docstore.add_documents.assert_called_with(
        [mock_node], allow_update=True
    )
    # Should update keyword table
    assert "kw" in mock_index.index_struct.table
    assert mock_index.index_struct.table["kw"] == ["node2"]
    # Should call _save_index_to_disc
    rag._save_index_to_disc.assert_called()
    # Should return the index
    assert result == mock_index
