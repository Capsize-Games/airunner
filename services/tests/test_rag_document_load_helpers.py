"""Unit tests for the RAG document loading helpers.

_load_dict_document_into_rag and _load_bytes_document_into_rag
were extracted to keep _load_documents_into_rag within the
long-function threshold. These tests pin the by-type routing and
the extension normalization.
"""

from unittest.mock import MagicMock

from airunner_services.workers.llm_generate_worker import LLMGenerateWorker


def _make_worker():
    worker = LLMGenerateWorker.__new__(LLMGenerateWorker)
    worker._model_manager = MagicMock()
    worker._model_manager_lock = MagicMock()
    worker._model_manager_lock.__enter__ = MagicMock(return_value=None)
    worker._model_manager_lock.__exit__ = MagicMock(return_value=False)
    worker.logger = MagicMock()
    return worker


def test_dict_html_loads_as_file():
    worker = _make_worker()
    worker._load_dict_document_into_rag(
        {"file_type": ".html", "content": "file.html"}
    )
    worker.model_manager.load_file_into_rag.assert_called_once_with(
        "file.html", source_name="web_content"
    )


def test_dict_pdf_routes_to_bytes_loader():
    worker = _make_worker()
    worker._load_bytes_document_into_rag = MagicMock()
    worker._load_dict_document_into_rag({"file_type": "pdf", "content": b"x"})
    worker._load_bytes_document_into_rag.assert_called_once()


def test_dict_unknown_type_falls_back_to_html():
    worker = _make_worker()
    worker._load_dict_document_into_rag({"file_type": "txt", "content": "hi"})
    worker.model_manager.load_html_into_rag.assert_called_once_with(
        "hi", source_name="web_content"
    )


def test_bytes_doc_uses_given_source_name():
    worker = _make_worker()
    worker._load_bytes_document_into_rag(
        b"data", "epub", {"source_name": "custom"}
    )
    worker.model_manager.load_bytes_into_rag.assert_called_once_with(
        b"data", source_name="custom", file_ext=".epub"
    )


def test_bytes_doc_defaults_source_name_and_normalizes_ext():
    worker = _make_worker()
    worker._load_bytes_document_into_rag("text", "PDF", {})
    worker.model_manager.load_bytes_into_rag.assert_called_once_with(
        b"text", source_name="pdf_upload", file_ext=".pdf"
    )


def test_bytes_doc_already_dotted_ext_unchanged():
    worker = _make_worker()
    worker._load_bytes_document_into_rag(b"data", ".mobi", {})
    worker.model_manager.load_bytes_into_rag.assert_called_once_with(
        b"data", source_name="mobi_upload", file_ext=".mobi"
    )
