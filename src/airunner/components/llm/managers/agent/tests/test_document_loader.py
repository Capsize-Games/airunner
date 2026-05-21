"""Tests for LangChain-native document loading helpers."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock


def test_load_documents_from_mobi_uses_extracted_epub(monkeypatch, tmp_path):
    """RAG ingestion should route MOBI files through extracted EPUB data."""
    from airunner.components.llm.managers.agent import document_loader as module

    mobi_path = tmp_path / "book.mobi"
    mobi_path.write_bytes(b"mobi-data")
    cleanup = Mock()
    epub_loader = Mock(return_value=[SimpleNamespace(page_content="text")])
    monkeypatch.setattr(module.shutil, "rmtree", cleanup)
    monkeypatch.setitem(module._FILE_LOADERS, ".epub", epub_loader)
    monkeypatch.setitem(
        sys.modules,
        "mobi",
        SimpleNamespace(
            extract=lambda _path: (
                "/tmp/mobi-rag",
                "/tmp/mobi-rag/book.epub",
            )
        ),
    )

    documents = module.load_documents_from_file(str(mobi_path))

    assert documents == [SimpleNamespace(page_content="text")]
    epub_loader.assert_called_once()
    cleanup.assert_called_once_with("/tmp/mobi-rag", ignore_errors=True)