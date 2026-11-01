"""Focused data-integrity and streaming-ingestion regressions."""

from __future__ import annotations

import importlib
import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from langchain_core.documents import Document


def test_bootstrap_downgrade_rejects_without_overwriting_user_values(
    tmp_path: Path,
) -> None:
    """The no-provenance downgrade fails before touching bootstrap rows."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    migration = importlib.import_module(
        "airunner_services.database.alembic.versions."
        "449cbcdca2c4_update_bootstrap_data"
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "CREATE TABLE image_filter_settings "
                    "(id INTEGER PRIMARY KEY, name TEXT)"
                )
            )
            connection.execute(
                sa.text(
                    "CREATE TABLE image_filter_values ("
                    "id INTEGER PRIMARY KEY, image_filter_id INTEGER, "
                    "name TEXT, value TEXT, value_type TEXT, "
                    "min_value REAL, max_value REAL)"
                )
            )
            connection.execute(
                sa.text("INSERT INTO image_filter_settings VALUES (1, 'color_balance')")
            )
            connection.execute(
                sa.text(
                    "INSERT INTO image_filter_values VALUES "
                    "(1, 1, 'cyan_red', '0.73', 'float', -1, 1)"
                )
            )
        with engine.connect() as connection:
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                migration.upgrade()
                before = connection.execute(
                    sa.text(
                        "SELECT name, value FROM image_filter_values "
                        "WHERE image_filter_id = 1 ORDER BY name"
                    )
                ).all()
                assert len(before) == 3
                assert ("cyan_red", "0.73") in before
                with pytest.raises(RuntimeError, match="no per-row provenance"):
                    migration.downgrade()
                after = connection.execute(
                    sa.text(
                        "SELECT name, value FROM image_filter_values "
                        "WHERE image_filter_id = 1 ORDER BY name"
                    )
                ).all()
                assert after == before
    finally:
        engine.dispose()


def _install_fake_zim_reader(monkeypatch, article_count: int) -> list[str]:
    """Install a deterministic fake reader and return its article paths."""
    paths = [f"article_{index}" for index in range(article_count)]
    fake_reader = types.ModuleType("airunner_services.zimreader")

    class FakeZimReader:
        def __init__(self, _path: str):
            pass

        def get_all_entry_paths(self, limit: int | None = None):
            return paths[:limit]

        def get_article(self, path: str):
            return f"<html><body><p>{path}</p></body></html>"

    fake_reader.ZIMReader = FakeZimReader
    monkeypatch.setitem(sys.modules, "airunner_services.zimreader", fake_reader)
    return paths


def test_zim_batches_stream_and_legacy_loader_still_returns_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The iterator yields bounded batches while list callers keep support."""
    from airunner_services.llm.managers.agent import document_loader

    path = tmp_path / "library.zim"
    path.write_bytes(b"fixture")
    article_paths = _install_fake_zim_reader(monkeypatch, 103)

    batches = list(document_loader.iter_document_batches_from_file(str(path)))
    assert [len(batch) for batch in batches] == [50, 50, 3]
    assert [
        batch_item.metadata["zim_path"]
        for batch in batches
        for batch_item in batch
    ] == article_paths

    legacy_documents = document_loader.load_documents_from_file(str(path))
    assert len(legacy_documents) == 103
    assert legacy_documents[0].metadata["zim_path"] == article_paths[0]


def test_per_document_index_consumes_zim_batches_incrementally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The persisted per-document index never requests a flattened ZIM list."""
    from airunner_services.llm.managers.agent.mixins import rag_indexing_mixin

    requested: list[str] = []
    batches = [
        [Document(page_content="first", metadata={})],
        [Document(page_content="second", metadata={})],
    ]

    def iter_batches(_path, _metadata_loader):
        for index, batch in enumerate(batches):
            requested.append(f"yield-{index}")
            yield batch

    class FakeIndex:
        def __init__(self, documents):
            self.documents = list(documents)
            self.added = []
            self.persisted = False

        @classmethod
        def from_documents(cls, documents, _embedding, _splitter):
            requested.append("first-index")
            return cls(documents)

        def add_documents(self, documents, _embedding, _splitter):
            requested.append("add-next")
            self.documents.extend(documents)
            self.added.extend(documents)

        def persist(self, _directory):
            self.persisted = True

    monkeypatch.setattr(
        rag_indexing_mixin,
        "iter_document_batches_from_file",
        iter_batches,
    )
    monkeypatch.setattr(rag_indexing_mixin, "DocumentVectorIndex", FakeIndex)

    class FakeIndexer:
        embedding = object()
        text_splitter = object()
        logger = logging.getLogger("test-zim-index")

        def __init__(self):
            self._loaded_doc_ids = []
            self.updated = None
            self.marked = None
            self.index = None

        def _setup_rag(self):
            pass

        @staticmethod
        def _generate_doc_id(_path):
            return "doc-1"

        @staticmethod
        def _extract_metadata(_path):
            return {"source": "test"}

        @staticmethod
        def _get_doc_index_dir(_doc_id, _path):
            return str(tmp_path / "index")

        def _update_registry_entry(self, doc_id, path, count):
            self.updated = (doc_id, path, count)

        def _mark_document_indexed(self, path):
            self.marked = path

    indexer = FakeIndexer()
    assert rag_indexing_mixin.RAGIndexingMixin._index_single_document(
        indexer, SimpleNamespace(path="library.zim")
    )
    assert requested == ["yield-0", "first-index", "yield-1", "add-next"]
    assert indexer.updated == ("doc-1", "library.zim", 2)
    assert indexer.marked == "library.zim"
    assert indexer._loaded_doc_ids == ["library.zim"]


def test_unified_ingestion_rolls_back_partial_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later batch failure cannot leave a partial index marked as loaded."""
    from airunner_services.llm.managers.agent.mixins import rag_lifecycle_mixin

    path = tmp_path / "library.zim"
    path.write_bytes(b"fixture")
    docs = [
        [Document(page_content="first", metadata={})],
        [Document(page_content="second", metadata={})],
    ]

    def iter_batches(_path, _metadata_loader):
        yield docs[0]
        yield docs[1]

    class FakeIndex:
        @classmethod
        def from_documents(cls, documents, _embedding, _splitter):
            instance = cls()
            instance.documents = list(documents)
            instance.embeddings = None
            return instance

        def add_documents(self, documents, _embedding, _splitter):
            self.documents.extend(documents)
            raise ValueError("synthetic add failure")

    monkeypatch.setattr(
        rag_lifecycle_mixin,
        "iter_document_batches_from_file",
        iter_batches,
    )
    monkeypatch.setattr(rag_lifecycle_mixin, "DocumentVectorIndex", FakeIndex)

    lifecycle = rag_lifecycle_mixin.RAGLifecycleMixin()
    lifecycle.embedding = object()
    lifecycle.text_splitter = object()
    lifecycle.logger = logging.getLogger("test-zim-unified")
    lifecycle._setup_rag = lambda: None
    lifecycle._loaded_doc_ids = []
    lifecycle._extract_metadata = lambda _path: {}
    lifecycle.load_file_into_rag(str(path))
    assert lifecycle._index is None
    assert lifecycle._loaded_doc_ids == []
