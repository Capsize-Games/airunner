"""Unit tests for RAG tool result formatting."""

from types import SimpleNamespace

from airunner.components.llm.tools.rag_tools import rag_search


def test_rag_search_includes_document_identity_before_excerpts():
    """RAG results should expose document identity before raw excerpts."""
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
    assert "Relevant excerpts:" in result
    assert result.index("Matched documents:") < result.index(
        "Relevant excerpts:"
    )
    assert (
        "[Excerpt 1 from The Satanic Bible - Anton LaVey.pdf]" in result
    )
