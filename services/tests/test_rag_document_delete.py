"""Generic document deletion cleans generated RAG state transactionally."""

from __future__ import annotations

import json
import logging
import shutil
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from airunner_services.database.models.document import Document as DBDocument
from airunner_services.llm.rag_mixin import RAGMixin


class _Session:
    def __init__(self, documents, *, fail_commit=False):
        self.documents = documents
        self.deleted = []
        self.fail_commit = fail_commit

    def query(self, model):
        self.select_ids = model is not DBDocument
        return self

    def filter(self, _expression):
        return self

    def all(self):
        if self.select_ids:
            return [(document.id,) for document in self.documents]
        return list(self.documents)

    def delete(self, document):
        self.deleted.append(document)
        self.documents.remove(document)

    def flush(self):
        pass


def _setup(tmp_path, monkeypatch, *, record_count=1, fail_commit=False):
    records = []
    sources = []
    for index in range(record_count):
        source = tmp_path / (
            "source.txt" if index == 0 else f"source-{index}.txt"
        )
        source.write_text(f"keep source {index}", encoding="utf-8")
        sources.append(source)
        records.append(SimpleNamespace(id=17 + index, path=str(source)))
    source = sources[0]
    record = records[0]
    session = _Session(records, fail_commit=fail_commit)

    @contextmanager
    def session_scope():
        before = list(session.documents)
        try:
            yield session
        except BaseException:
            session.documents[:] = before
            raise
        if session.fail_commit:
            session.fail_commit = False
            session.documents[:] = before
            raise OSError("database commit failed")

    monkeypatch.setattr(
        "airunner_services.llm.managers.agent.mixins.rag_index_management_mixin.session_scope",
        session_scope,
    )
    rag = RAGMixin()
    rag.logger = logging.getLogger("rag-delete-test")
    rag.path_settings = SimpleNamespace(
        base_path=str(tmp_path), rag_index_path=str(tmp_path / "rag")
    )
    registry_documents = {}
    indexes = []
    for row in records:
        doc_id = rag._generate_doc_id(row.path)
        index_dir = Path(rag._get_doc_index_dir(doc_id, row.path))
        index_dir.mkdir(parents=True)
        (index_dir / "documents.json").write_text("[]", encoding="utf-8")
        indexes.append((doc_id, index_dir))
        registry_documents[doc_id] = {"path": row.path}
    doc_id, current_index = indexes[0]
    rag._index_registry = {
        "version": "2.0",
        "documents": registry_documents,
    }
    rag._save_registry()
    return (
        rag,
        record,
        session,
        source,
        current_index,
        doc_id,
        records,
        indexes,
        sources,
    )


def test_delete_removes_index_registry_row_and_cache_but_preserves_source(
    tmp_path, monkeypatch
):
    rag, record, session, source, current_index, doc_id, *_ = _setup(
        tmp_path, monkeypatch
    )
    rag._doc_indexes_cache[doc_id] = object()
    rag._loaded_doc_ids.append(doc_id)

    result = rag.delete_document_records([record.id])

    assert result == {"deleted": True, "count": 1, "cleanup_pending": []}
    assert session.deleted == [record]
    assert not session.documents
    assert not current_index.exists()
    assert doc_id not in rag._index_registry["documents"]
    assert doc_id not in rag._doc_indexes_cache
    assert doc_id not in rag._loaded_doc_ids
    assert source.read_text(encoding="utf-8") == "keep source 0"


def test_registry_failure_restores_index_and_leaves_database_row(
    tmp_path, monkeypatch
):
    rag, record, session, source, current_index, doc_id, *_ = _setup(
        tmp_path, monkeypatch
    )
    original_registry = Path(rag.registry_path).read_bytes()
    module = "airunner_services.llm.managers.agent.mixins.rag_index_management_mixin"
    monkeypatch.setattr(
        f"{module}._write_json_atomically",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        rag.delete_document_records([record.id])

    assert session.documents == [record]
    assert not session.deleted
    assert current_index.is_dir()
    assert Path(rag.registry_path).read_bytes() == original_registry
    assert source.exists()
    assert doc_id in rag.index_registry["documents"]


def test_bulk_registry_failure_restores_every_staged_index(tmp_path, monkeypatch):
    rag, _record, session, _source, _index, _doc_id, records, indexes, _sources = _setup(
        tmp_path, monkeypatch, record_count=2
    )
    original_registry = Path(rag.registry_path).read_bytes()
    module = __import__(
        "airunner_services.llm.managers.agent.mixins.rag_index_management_mixin",
        fromlist=["_write_json_atomically"],
    )
    original_write = module._write_json_atomically

    def fail_registry_write(path, payload):
        if path == rag.registry_path:
            raise OSError("registry write failed")
        return original_write(path, payload)

    monkeypatch.setattr(module, "_write_json_atomically", fail_registry_write)
    with pytest.raises(OSError, match="registry write failed"):
        rag.delete_document_records([record.id for record in records])

    assert session.documents == records
    assert Path(rag.registry_path).read_bytes() == original_registry
    assert all(index_path.is_dir() for _doc_id, index_path in indexes)


def test_database_commit_failure_restores_registry_and_staged_index(
    tmp_path, monkeypatch
):
    rag, record, session, source, current_index, doc_id, *_ = _setup(
        tmp_path, monkeypatch, fail_commit=True
    )
    original_registry = Path(rag.registry_path).read_bytes()

    with pytest.raises(OSError, match="database commit failed"):
        rag.delete_document_records([record.id])

    assert session.documents == [record]
    assert current_index.is_dir()
    assert Path(rag.registry_path).read_bytes() == original_registry
    assert doc_id in rag.index_registry["documents"]
    assert source.exists()
    assert not Path(rag._pending_index_cleanup_path()).exists()


def test_post_commit_cleanup_failure_is_persisted_and_retried(
    tmp_path, monkeypatch
):
    rag, record, _session, source, current_index, _doc_id, *_ = _setup(
        tmp_path, monkeypatch
    )
    original_rmtree = shutil.rmtree
    module = "airunner_services.llm.managers.agent.mixins.rag_index_management_mixin"
    monkeypatch.setattr(
        f"{module}.shutil.rmtree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("busy")),
    )

    result = rag.delete_document_records([record.id])

    assert result["cleanup_pending"]
    manifest = Path(rag._pending_index_cleanup_path())
    journal = json.loads(manifest.read_text(encoding="utf-8"))
    operation = journal["operations"][0]
    assert operation["phase"] == "committed"
    assert len(operation["directories"]) == 1
    staged = Path(operation["directories"][0]["staged"])
    assert staged.is_dir()
    assert not current_index.exists()
    assert source.exists()

    monkeypatch.setattr(shutil, "rmtree", original_rmtree)
    rag._retry_pending_index_cleanup()
    assert not staged.exists()
    assert not manifest.exists()


def test_post_commit_journal_write_failure_keeps_recovery_owner(
    tmp_path, monkeypatch
):
    rag, record, session, source, current_index, doc_id, *_ = _setup(
        tmp_path, monkeypatch
    )
    rag._doc_indexes_cache[doc_id] = object()
    original_store = rag._store_deletion_operation

    def fail_committed_phase(operation):
        if operation["phase"] == "committed":
            raise OSError("journal unavailable")
        return original_store(operation)

    monkeypatch.setattr(rag, "_store_deletion_operation", fail_committed_phase)
    result = rag.delete_document_records([record.id])

    manifest = Path(rag._pending_index_cleanup_path())
    assert result["deleted"] is True
    assert result["cleanup_pending"] == [str(manifest)]
    assert not session.documents
    assert not current_index.exists()
    assert source.exists()
    assert doc_id not in rag._index_registry["documents"]
    assert doc_id not in rag._doc_indexes_cache
    assert json.loads(manifest.read_text(encoding="utf-8"))["operations"][0][
        "phase"
    ] == "preparing"

    monkeypatch.setattr(rag, "_store_deletion_operation", original_store)
    rag._retry_pending_index_cleanup()
    assert not manifest.exists()


@pytest.mark.parametrize(
    "journal_mode", ["malformed", "symlink", "bad_suffix", "staged_symlink"]
)
def test_journal_rejects_corrupt_or_unsafe_cleanup_paths(
    tmp_path, monkeypatch, journal_mode
):
    rag, record, _session, _source, current_index, doc_id, *_ = _setup(
        tmp_path, monkeypatch
    )
    manifest = Path(rag._pending_index_cleanup_path())
    if journal_mode == "symlink":
        external = tmp_path / "external.json"
        external.write_text('{"safe": true}', encoding="utf-8")
        manifest.symlink_to(external)
    elif journal_mode == "malformed":
        manifest.write_text("[]", encoding="utf-8")
    else:
        staged_path = str(current_index)
        if journal_mode == "staged_symlink":
            external_index = tmp_path / "external-index"
            external_index.mkdir()
            (external_index / "source.txt").write_text("keep", encoding="utf-8")
            staged_path = f"{current_index}.delete-pending-{'b' * 32}"
            Path(staged_path).symlink_to(external_index, target_is_directory=True)
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "operations": [
                        {
                            "operation_id": "a" * 32,
                            "phase": "committed",
                            "document_records": [
                                {
                                    "id": record.id,
                                    "path": record.path,
                                    "doc_id": doc_id,
                                }
                            ],
                            "directories": [
                                {
                                    "doc_id": doc_id,
                                    "source_path": record.path,
                                    "original": str(current_index),
                                    "staged": staged_path,
                                }
                            ],
                            "registry_path": rag.registry_path,
                            "registry_before_b64": None,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    with pytest.raises((ValueError, OSError)):
        rag._retry_pending_index_cleanup()
    assert current_index.is_dir()
    if journal_mode == "staged_symlink":
        assert (tmp_path / "external-index" / "source.txt").read_text(
            encoding="utf-8"
        ) == "keep"


@pytest.mark.parametrize("crash_phase", ["preparing", "committed"])
def test_journal_recovers_crashes_around_database_commit(
    tmp_path, monkeypatch, crash_phase
):
    rag, record, session, source, current_index, doc_id, *_ = _setup(
        tmp_path, monkeypatch
    )
    module = __import__(
        "airunner_services.llm.managers.agent.mixins.rag_index_management_mixin",
        fromlist=["_store_deletion_operation", "_write_json_atomically"],
    )
    if crash_phase == "preparing":
        original_write = module._write_json_atomically

        def crash_after_registry_write(path, payload):
            original_write(path, payload)
            if path == rag.registry_path:
                raise KeyboardInterrupt("simulated process interruption")

        monkeypatch.setattr(module, "_write_json_atomically", crash_after_registry_write)
    else:
        original_store = rag._store_deletion_operation

        def crash_before_commit_journal_update(operation):
            if operation["phase"] == "committed":
                raise KeyboardInterrupt("simulated process interruption")
            original_store(operation)

        monkeypatch.setattr(rag, "_store_deletion_operation", crash_before_commit_journal_update)

    with pytest.raises(KeyboardInterrupt):
        rag.delete_document_records([record.id])

    restarted = RAGMixin()
    restarted.logger = logging.getLogger("rag-delete-recovery-test")
    restarted.path_settings = rag.path_settings
    registry = restarted.index_registry
    if crash_phase == "preparing":
        assert session.documents == [record]
        assert current_index.is_dir()
        assert doc_id in registry["documents"]
        assert source.exists()
    else:
        assert not session.documents
        assert not current_index.exists()
        assert doc_id not in registry["documents"]
        assert source.exists()
    assert not Path(restarted._pending_index_cleanup_path()).exists()


def test_mixed_database_recovery_fails_closed_and_retains_staging(
    tmp_path, monkeypatch
):
    rag, _record, session, _source, _index, _doc_id, records, indexes, _sources = _setup(
        tmp_path, monkeypatch, record_count=2
    )
    module = __import__(
        "airunner_services.llm.managers.agent.mixins.rag_index_management_mixin",
        fromlist=["_write_json_atomically"],
    )
    original_replace = module.os.replace
    staged_paths = []

    def interrupt_after_first_rename(source, destination):
        result = original_replace(source, destination)
        if str(destination).endswith(".delete-pending-") or ".delete-pending-" in str(destination):
            staged_paths.append(Path(destination))
            raise KeyboardInterrupt("simulated interruption")
        return result

    monkeypatch.setattr(module.os, "replace", interrupt_after_first_rename)
    with pytest.raises(KeyboardInterrupt):
        rag.delete_document_records([record.id for record in records])
    monkeypatch.setattr(module.os, "replace", original_replace)

    # Model a torn/partially durable database commit. Recovery must not guess.
    session.documents.remove(records[0])
    restarted = RAGMixin()
    restarted.logger = logging.getLogger("rag-delete-mixed-recovery-test")
    restarted.path_settings = rag.path_settings
    with pytest.raises(RuntimeError, match="mixed database state"):
        _ = restarted.index_registry

    assert staged_paths and staged_paths[0].exists()
    assert Path(restarted._pending_index_cleanup_path()).exists()
    assert indexes[1][1].is_dir()


def test_recovery_precedes_a_later_index_registry_mutation(tmp_path, monkeypatch):
    rag, record, _session, _source, current_index, doc_id, *_ = _setup(
        tmp_path, monkeypatch
    )
    module = __import__(
        "airunner_services.llm.managers.agent.mixins.rag_index_management_mixin",
        fromlist=["_write_json_atomically"],
    )
    original_write = module._write_json_atomically

    def crash_after_registry_write(path, payload):
        original_write(path, payload)
        if path == rag.registry_path:
            raise KeyboardInterrupt("simulated interruption")

    monkeypatch.setattr(module, "_write_json_atomically", crash_after_registry_write)
    with pytest.raises(KeyboardInterrupt):
        rag.delete_document_records([record.id])
    monkeypatch.setattr(module, "_write_json_atomically", original_write)

    restarted = RAGMixin()
    restarted.logger = logging.getLogger("rag-delete-next-mutation-test")
    restarted.path_settings = rag.path_settings
    # First subsequent registry access resolves the journal before exposing state.
    assert doc_id in restarted.index_registry["documents"]
    assert current_index.is_dir()
    assert not Path(restarted._pending_index_cleanup_path()).exists()
