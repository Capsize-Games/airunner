"""Worker routes explicit reindex requests to the staged agent operation."""

from __future__ import annotations

from types import SimpleNamespace

from airunner_services.llm.workers.mixins import rag_indexing_mixin as worker_module
from airunner_services.llm.workers.rag_index_admission import (
    rag_index_cancel_requested,
    release_rag_index_job,
    request_rag_index_cancel,
    reserve_rag_index_job,
)


def _worker(agent):
    worker = worker_module.RAGIndexingMixin()
    worker.model_manager = SimpleNamespace(agent=agent)
    worker.logger = SimpleNamespace(
        info=lambda *a, **k: None,
        error=lambda *a, **k: None,
        warning=lambda *a, **k: None,
    )
    worker.emit_signal = lambda *args: None
    worker._validate_document_path = lambda path: path
    worker._get_document_from_db = lambda path: SimpleNamespace(id=1, path=path)
    return worker


def test_reindex_worker_invokes_staged_operation(monkeypatch):
    calls = []
    agent = SimpleNamespace(
        _reindex_single_document=lambda document: calls.append(document.path) or True
    )
    worker = _worker(agent)
    monkeypatch.setattr(
        worker_module,
        "DBDocument",
        SimpleNamespace(objects=SimpleNamespace(update=lambda **_kwargs: None)),
    )

    assert worker._validate_indexing_support(reindex=True)
    assert worker._index_single_file("/documents/a.pdf", 0, 1, reindex=True)
    assert calls == ["/documents/a.pdf"]


def test_manual_index_worker_uses_safe_existing_index_dispatch(monkeypatch):
    calls = []
    agent = SimpleNamespace(
        _index_or_reindex_document=lambda document: calls.append(document.path) or True
    )
    worker = _worker(agent)
    monkeypatch.setattr(
        worker_module,
        "DBDocument",
        SimpleNamespace(objects=SimpleNamespace(update=lambda **_kwargs: None)),
    )

    assert worker._validate_indexing_support(reindex=False)
    assert worker._index_single_file("/documents/a.pdf", 0, 1, reindex=False)
    assert calls == ["/documents/a.pdf"]


def test_reindex_cancel_stops_before_another_document():
    calls = []
    agent = SimpleNamespace(
        _reindex_single_document=lambda document: calls.append(document.path) or True
    )
    worker = _worker(agent)
    token = reserve_rag_index_job()
    assert token is not None
    request_rag_index_cancel()
    emitted = []
    worker.emit_signal = lambda *args: emitted.append(args)

    try:
        worker._index_documents(["/documents/a.pdf"], reindex=True)

        assert calls == []
        assert emitted[-1][1]["success"] is False
        assert "cancelled" in emitted[-1][1]["message"]
    finally:
        release_rag_index_job(token)


def test_competing_worker_does_not_clear_owner_cancel_or_status():
    token = reserve_rag_index_job()
    assert token is not None
    request_rag_index_cancel()
    agent = SimpleNamespace(_reindex_single_document=lambda _document: True)
    worker = _worker(agent)
    status_starts = []
    monkeypatch_status = worker_module.rag_index_status_tracker.start
    worker_module.rag_index_status_tracker.start = lambda **kwargs: status_starts.append(kwargs)
    try:
        worker.on_rag_index_selected_documents_signal(
            {"file_paths": ["/documents/other.pdf"], "reindex": True}
        )
        assert rag_index_cancel_requested()
        assert status_starts == []
    finally:
        worker_module.rag_index_status_tracker.start = monkeypatch_status
        release_rag_index_job(token)
