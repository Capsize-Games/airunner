"""Unit tests for request-attached document indexing state sync."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.managers.agent.mixins import (
    rag_indexing_mixin as module,
)
from airunner.components.llm.managers.agent.mixins.rag_indexing_mixin import (
    EmbeddingModelDownloadPendingError,
    RAGIndexingMixin,
)
from airunner.enums import SignalCode


class _DummyRAGIndexingMixin(RAGIndexingMixin):
    def __init__(self):
        self.logger = Mock()
        self._setup_rag = Mock()
        self._retriever = object()
        self._index_single_document = Mock(return_value=True)
        self.emit_signal = Mock()


def test_ensure_indexed_files_promotes_request_documents(monkeypatch):
    """Attached request docs should become indexed and active in the DB."""
    db_doc = SimpleNamespace(
        id=7,
        path="/tmp/doc.pdf",
        indexed=False,
        active=False,
    )

    def filter_by(path):
        return [db_doc] if path == db_doc.path else []

    update = Mock(
        side_effect=lambda pk, **kwargs: [
            setattr(db_doc, key, value) for key, value in kwargs.items()
        ]
    )

    monkeypatch.setattr(module.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        module,
        "DBDocument",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=filter_by,
                create=Mock(),
                update=update,
            )
        ),
    )

    mixin = _DummyRAGIndexingMixin()

    assert mixin.ensure_indexed_files(["/tmp/doc.pdf"]) is True

    mixin._setup_rag.assert_called_once_with()
    mixin._index_single_document.assert_called_once_with(db_doc)
    update.assert_called_once_with(pk=7, active=True)
    assert mixin._retriever is None
    mixin.emit_signal.assert_any_call(
        SignalCode.DOCUMENT_INDEXED,
        {"path": "/tmp/doc.pdf"},
    )
    mixin.emit_signal.assert_any_call(
        SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"paths": ["/tmp/doc.pdf"]},
    )


def test_ensure_indexed_files_activates_already_indexed_documents(monkeypatch):
    """Already indexed request docs should still become active."""
    db_doc = SimpleNamespace(
        id=9,
        path="/tmp/doc.pdf",
        indexed=True,
        active=False,
    )

    update = Mock(
        side_effect=lambda pk, **kwargs: [
            setattr(db_doc, key, value) for key, value in kwargs.items()
        ]
    )

    monkeypatch.setattr(module.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        module,
        "DBDocument",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [db_doc],
                create=Mock(),
                update=update,
            )
        ),
    )

    mixin = _DummyRAGIndexingMixin()

    assert mixin.ensure_indexed_files(["/tmp/doc.pdf"]) is True

    mixin._index_single_document.assert_not_called()
    update.assert_called_once_with(pk=9, active=True)
    mixin.emit_signal.assert_called_once_with(
        SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"paths": ["/tmp/doc.pdf"]},
    )


def test_ensure_indexed_files_marks_retry_after_download(monkeypatch):
    """Attached docs should request retry while embeddings download."""
    db_doc = SimpleNamespace(
        id=11,
        path="/tmp/doc.pdf",
        indexed=False,
        active=False,
    )

    monkeypatch.setattr(module.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        module,
        "DBDocument",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [db_doc],
                create=Mock(),
                update=Mock(),
            )
        ),
    )

    mixin = _DummyRAGIndexingMixin()
    mixin._index_single_document.side_effect = (
        EmbeddingModelDownloadPendingError(
            "Embedding model download in progress."
        )
    )

    assert mixin.ensure_indexed_files(["/tmp/doc.pdf"]) is False

    assert mixin._rag_retry_after_download is True
    assert mixin._last_rag_index_error == (
        "Embedding model download in progress."
    )
    mixin.emit_signal.assert_not_called()


def test_ensure_indexed_files_resolves_managed_copy(monkeypatch):
    """Missing request paths should reuse an existing managed document."""
    db_doc = SimpleNamespace(
        id=13,
        path="/library/doc.pdf",
        indexed=False,
        active=False,
    )

    update = Mock(
        side_effect=lambda pk, **kwargs: [
            setattr(db_doc, key, value) for key, value in kwargs.items()
        ]
    )

    monkeypatch.setattr(
        module.os.path,
        "exists",
        lambda path: path == "/library/doc.pdf",
    )
    monkeypatch.setattr(
        module,
        "DBDocument",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [db_doc] if path == db_doc.path else [],
                all=lambda: [db_doc],
                create=Mock(),
                update=update,
            )
        ),
    )

    mixin = _DummyRAGIndexingMixin()

    assert mixin.ensure_indexed_files(["/tmp/doc.pdf"]) is True

    mixin._index_single_document.assert_called_once_with(db_doc)
    update.assert_called_once_with(pk=13, active=True)
    mixin.emit_signal.assert_any_call(
        SignalCode.DOCUMENT_INDEXED,
        {"path": "/library/doc.pdf"},
    )
    mixin.emit_signal.assert_any_call(
        SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"paths": ["/library/doc.pdf"]},
    )