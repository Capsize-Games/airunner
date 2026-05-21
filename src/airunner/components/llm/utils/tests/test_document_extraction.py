"""Tests for document extraction helpers."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock


def test_extract_text_dispatches_to_mobi_extractor(monkeypatch, tmp_path):
    """The extension dispatcher should route MOBI files explicitly."""
    from airunner.components.llm.utils import document_extraction as module

    mobi_path = tmp_path / "book.mobi"
    mobi_path.write_bytes(b"mobi-data")
    mobi_extract = Mock(return_value="converted")
    monkeypatch.setattr(module, "extract_text_from_mobi", mobi_extract)

    assert module.extract_text(str(mobi_path)) == "converted"
    mobi_extract.assert_called_once_with(str(mobi_path))


def test_extract_text_from_mobi_uses_epub_output(monkeypatch):
    """Converted MOBI EPUB output should flow through the EPUB extractor."""
    from airunner.components.llm.utils import document_extraction as module

    cleanup = Mock()
    epub_extract = Mock(return_value="ebook text")
    monkeypatch.setattr(module.shutil, "rmtree", cleanup)
    monkeypatch.setattr(module, "extract_text_from_epub", epub_extract)
    monkeypatch.setitem(
        sys.modules,
        "mobi",
        SimpleNamespace(
            extract=lambda _path: (
                "/tmp/mobi-work",
                "/tmp/mobi-work/book.epub",
            )
        ),
    )

    assert module.extract_text_from_mobi("/tmp/book.mobi") == "ebook text"
    epub_extract.assert_called_once_with("/tmp/mobi-work/book.epub")
    cleanup.assert_called_once_with("/tmp/mobi-work", ignore_errors=True)