"""Unit tests for RAG tool result formatting."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.tools.rag_tools import rag_search


def test_rag_search_includes_document_identity_before_excerpts():
    """Identity queries should return document metadata without excerpts."""
    doc = SimpleNamespace(
        metadata={
            "source": "/library/The Satanic Bible - Anton LaVey.pdf",
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": "/library/The Satanic Bible - Anton LaVey.pdf",
        },
        page_content="Opening excerpt from the attached document.",
    )
    api = SimpleNamespace(search=lambda query, k=3: [doc])

    result = rag_search("what is this document?", api=api)

    assert "Matched documents:" in result
    assert (
        "Document 1: The Satanic Bible - Anton LaVey.pdf" in result
    )
    assert (
        "Inferred title from filename: The Satanic Bible" in result
    )
    assert "Inferred author from filename: Anton LaVey" in result
    assert "Relevant excerpts:" not in result


def test_rag_search_keeps_excerpts_for_content_queries():
    """Content questions should still include matched excerpts."""
    doc = SimpleNamespace(
        metadata={
            "source": "/library/The Satanic Bible - Anton LaVey.pdf",
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": "/library/The Satanic Bible - Anton LaVey.pdf",
        },
        page_content="Opening excerpt from the attached document.",
    )
    api = SimpleNamespace(search=lambda query, k=3: [doc])

    result = rag_search("summarize this document", api=api)

    assert "Matched documents:" in result
    assert "Relevant excerpts:" in result
    assert result.index("Matched documents:") < result.index(
        "Relevant excerpts:"
    )
    assert (
        "[Excerpt 1 from The Satanic Bible - Anton LaVey.pdf]" in result
    )


def test_rag_search_expands_single_document_pronoun_queries():
    """Single-document follow-ups should include the active doc name."""
    doc = SimpleNamespace(
        metadata={
            "source": "/library/The Satanic Bible - Anton LaVey.pdf",
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": "/library/The Satanic Bible - Anton LaVey.pdf",
        },
        page_content="Contents page excerpt.",
    )
    search = Mock(return_value=[doc])
    api = SimpleNamespace(
        search=search,
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    rag_search("what are the chapters in it?", api=api)

    effective_query = search.call_args.args[0]
    assert "what are the chapters in it?" in effective_query
    assert "The Satanic Bible" in effective_query
    assert "Anton LaVey" in effective_query
