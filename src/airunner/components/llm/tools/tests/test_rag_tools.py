"""Unit tests for RAG tool result formatting."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from airunner.components.llm.tools.rag_tools import (
    inspect_loaded_documents,
    rag_search,
    save_to_knowledge_base,
)


def test_rag_search_returns_metadata_and_excerpts_for_document_queries():
    """RAG search should stay generic and always return evidence."""
    doc = SimpleNamespace(
        metadata={
            "source": "/library/The Satanic Bible - Anton LaVey.pdf",
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": "/library/The Satanic Bible - Anton LaVey.pdf",
        },
        page_content="Opening excerpt from the attached document.",
    )
    api = SimpleNamespace(search=lambda query, k=6: [doc])

    result = rag_search("what is this document?", api=api)

    assert "Matched documents:" in result
    assert "Relevant excerpts:" in result
    assert (
        "Document 1: The Satanic Bible - Anton LaVey.pdf" in result
    )
    assert (
        "Inferred title from filename: The Satanic Bible" in result
    )
    assert "Inferred author from filename: Anton LaVey" in result
    assert (
        "[Excerpt 1 from The Satanic Bible - Anton LaVey.pdf]" in result
    )


def test_rag_search_uses_standard_retrieval_breadth():
    """Summary fallback retrieval should request a wider result set."""
    doc = SimpleNamespace(
        metadata={
            "source": "/library/The Satanic Bible - Anton LaVey.pdf",
            "file_name": "The Satanic Bible - Anton LaVey.pdf",
            "file_type": ".pdf",
            "file_path": "/library/The Satanic Bible - Anton LaVey.pdf",
        },
        page_content="Opening excerpt from the attached document.",
    )
    search = Mock(return_value=[doc])
    api = SimpleNamespace(
        search=search,
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    rag_search("summarize the document for me", api=api)

    assert search.call_args.kwargs["k"] == 12


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_rag_search_builds_summary_evidence_across_document(
    mock_resolve,
    mock_extract,
):
    """Summary intent should cover multiple document regions when possible."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "INTRODUCTION\n\n"
        "The introduction frames Satanism as a realism-first philosophy.\n\n"
        "THE BOOK OF SATAN\n\n"
        "This section rejects Christian mysticism and centers the real world.\n\n"
        "THE BOOK OF LUCIFER\n\n"
        "This section presents key arguments and practical philosophy.\n\n"
        "THE BOOK OF BELIAL\n\n"
        "This section focuses on ritual as applied practice.\n\n"
        "THE BOOK OF LEVIATHAN\n\n"
        "This section contains later material and ceremonial text."
    )
    search = Mock()
    api = SimpleNamespace(
        search=search,
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = rag_search("summarize the document for me", api=api)

    assert "Section: INTRODUCTION." in result
    assert "Section: THE BOOK OF SATAN." in result
    assert "Section: THE BOOK OF BELIAL." in result
    assert "Section: THE BOOK OF LEVIATHAN." in result
    search.assert_not_called()


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
def test_inspect_loaded_documents_returns_structure_for_single_active_doc(
    mock_resolve,
    mock_extract,
):
    """Inspection should expose active document metadata and structure."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = (
        "INTRODUCTION\n\nPROLOGUE\n\nTHE BOOK OF SATAN\n\n"
        "THE BOOK OF LUCIFER\n\nTHE BOOK OF BELIAL\n\n"
        "THE BOOK OF LEVIATHAN"
    )
    api = SimpleNamespace(
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = inspect_loaded_documents(api=api)

    assert "Loaded documents:" in result
    assert "Document structure:" in result
    assert "Inferred title from filename: The Satanic Bible" in result
    assert "1. INTRODUCTION" in result
    assert "3. THE BOOK OF SATAN" in result
    assert "6. THE BOOK OF LEVIATHAN" in result


@patch("airunner.components.llm.tools.rag_tools.extract_text")
@patch("airunner.components.llm.tools.rag_tools.resolve_existing_file")
def test_inspect_loaded_documents_returns_metadata_without_structure(
    mock_resolve,
    mock_extract,
):
    """Inspection should still return metadata when no headings exist."""
    file_path = "/library/The Satanic Bible - Anton LaVey.pdf"
    mock_resolve.return_value = file_path
    mock_extract.return_value = "Ordinary prose without heading markers."
    api = SimpleNamespace(
        _get_active_document_paths=lambda: [file_path],
        _get_active_document_names=lambda: [
            "The Satanic Bible - Anton LaVey.pdf"
        ],
    )

    result = inspect_loaded_documents(api=api)

    assert "Loaded documents:" in result
    assert "Document structure:" not in result
    assert (
        "Stored path: /library/The Satanic Bible - Anton LaVey.pdf"
        in result
    )


@patch("airunner.components.llm.tools.rag_tools.PathSettings.objects.first")
def test_save_to_knowledge_base_errors_without_path_settings(mock_first):
    """Saving KB content should fail clearly without a configured base path."""
    mock_first.return_value = None

    result = save_to_knowledge_base(
        "content",
        "Example",
        api=None,
    )

    assert "No knowledge base path is configured" in result
