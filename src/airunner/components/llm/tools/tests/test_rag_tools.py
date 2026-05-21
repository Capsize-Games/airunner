"""Unit tests for RAG tool result formatting."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

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


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_returns_document_structure_for_contents_queries(
    mock_resolve,
    mock_extract,
):
    """Contents questions should use extracted document headings."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "INTRODUCTION\n\nPROLOGUE\n\nTHE BOOK OF SATAN\n\n"
        "THE BOOK OF LUCIFER\n\nTHE BOOK OF BELIAL\n\n"
        "THE BOOK OF LEVIATHAN"
    )
    search = Mock(return_value=[])
    api = SimpleNamespace(
        search=search,
        _get_active_document_paths=lambda: [file_path],
    )

    result = rag_search("what chapters are in it?", api=api)

    assert "Document structure:" in result
    assert "1. INTRODUCTION" in result
    assert "3. THE BOOK OF SATAN" in result
    assert "6. THE BOOK OF LEVIATHAN" in result
    search.assert_not_called()


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_falls_back_when_structure_is_unavailable(
    mock_resolve,
    mock_extract,
):
    """Structure queries should fall back to vector search when needed."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "Ordinary prose without heading markers."
    doc = SimpleNamespace(
        metadata={
            "source": file_path,
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": file_path,
        },
        page_content="Contents page excerpt.",
    )
    search = Mock(return_value=[doc])
    api = SimpleNamespace(
        search=search,
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = rag_search("what chapters are in it?", api=api)

    search.assert_called_once()
    assert "Relevant excerpts:" in result
