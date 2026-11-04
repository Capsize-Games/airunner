"""Explicit RAG reindex replaces a complete persisted index transactionally."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from langchain_core.documents import Document

from airunner_services.llm.managers.agent.vector_index import DocumentVectorIndex
from airunner_services.llm.rag_mixin import RAGMixin
from airunner_services.runtimes import e5_model_identity as identity_module
from airunner_services.runtimes.e5_model_identity import E5ModelIdentity


def _identity():
    files = tuple(
        sorted((name, digest) for name, (_, digest) in identity_module.E5_MODEL_FILES.items())
    )
    return E5ModelIdentity(
        model_id=identity_module.E5_LARGE_MODEL_ID,
        revision=identity_module.E5_LARGE_REVISION,
        dimension=identity_module.E5_LARGE_DIMENSION,
        manifest_sha256=identity_module._manifest_digest(files),
        file_sha256=files,
    )


class _Embedder:
    verified_identity = _identity()

    def embed_documents(self, texts):
        return [[1.0] + [0.0] * 1023 for _ in texts]


class _Splitter:
    def split_documents(self, documents):
        chunks = []
        for document in documents:
            pieces = document.page_content.split("|")
            chunks.extend(
                Document(
                    page_content=piece,
                    metadata=dict(document.metadata),
                )
                for piece in pieces
            )
        return chunks


class _DocumentManager:
    def __init__(self, document):
        self.document = document

    def filter_by(self, **_kwargs):
        return [self.document]

    def update(self, *, pk, **fields):
        assert pk == self.document.id
        for name, value in fields.items():
            setattr(self.document, name, value)


class _DocumentModel:
    objects = None


def _make_rag(tmp_path, monkeypatch, *, fail_registry=False):
    source = tmp_path / "source.txt"
    source.write_text("new source", encoding="utf-8")
    document = SimpleNamespace(
        id=7,
        path=str(source),
        indexed=True,
        file_hash="old-hash",
        indexed_at="old-time",
        file_size=3,
    )
    _DocumentModel.objects = _DocumentManager(document)
    monkeypatch.setattr(
        "airunner_services.llm.managers.agent.mixins.rag_indexing_mixin.DBDocument",
        _DocumentModel,
    )
    monkeypatch.setattr(
        "airunner_services.llm.managers.agent.mixins.rag_document_mixin.DBDocument",
        _DocumentModel,
    )
    rag = RAGMixin()
    rag.logger = logging.getLogger("reindex-test")
    rag.path_settings = SimpleNamespace(
        base_path=str(tmp_path), rag_index_path=str(tmp_path / "rag")
    )
    rag._index_registry = {
        "documents": {
            "doc-1": {"path": str(source), "file_name": source.name}
        },
        "version": "2.0",
    }
    rag._embedding = _Embedder()
    rag._text_splitter = _Splitter()
    rag._setup_rag = lambda: None
    rag._generate_doc_id = lambda _path: "doc-1"
    rag._extract_metadata = lambda _path: {"source": "source.txt"}
    rag._doc_indexes_cache = {}
    rag._loaded_doc_ids = []
    index_dir = Path(rag._get_doc_index_dir("doc-1", str(source)))
    index_dir.mkdir(parents=True)
    old = DocumentVectorIndex(
        [Document(page_content="old content", metadata={"doc_id": "doc-1"})],
        np.asarray([[1.0, 0.0]], dtype=np.float32),
    )
    old.persist(str(index_dir))
    rag._save_registry()
    if fail_registry:
        rag._update_registry_entry = lambda *_args: (_ for _ in ()).throw(
            RuntimeError("registry failure")
        )
    return rag, document, index_dir


def test_explicit_reindex_switches_only_after_candidate_validation(
    tmp_path, monkeypatch
):
    from airunner_services.llm.managers.agent.mixins import rag_indexing_mixin

    rag, document, index_dir = _make_rag(tmp_path, monkeypatch)
    monkeypatch.setattr(
        rag_indexing_mixin,
        "iter_document_batches_from_file",
        lambda *_args: iter([[Document(page_content="chunk one|chunk two")]]),
    )

    assert rag._reindex_single_document(document)

    active = DocumentVectorIndex.load(str(index_dir))
    assert [document.page_content for document in active.documents] == [
        "chunk one",
        "chunk two",
    ]
    assert rag.index_registry["documents"]["doc-1"]["chunk_count"] == 2
    assert active.embedding_identity["manifest_sha256"] == _identity().manifest_sha256
    assert document.indexed is True
    assert document.file_hash == rag._calculate_file_hash(document.path)
    assert len(list(index_dir.parent.glob(index_dir.name + ".reindex-backup-*"))) == 1


def test_initial_index_refuses_to_overwrite_existing_index(tmp_path, monkeypatch):
    from airunner_services.llm.managers.agent.mixins.rag_indexing_mixin import (
        ReindexRequiredError,
    )

    rag, document, index_dir = _make_rag(tmp_path, monkeypatch)

    with pytest.raises(ReindexRequiredError, match="reindex_required"):
        rag._index_single_document(document)

    assert DocumentVectorIndex.load(str(index_dir)).documents[0].page_content == "old content"
    assert document.file_hash == "old-hash"
    assert not list(index_dir.parent.glob(index_dir.name + ".reindex-backup-*"))


def test_explicit_index_or_reindex_stages_existing_index(tmp_path, monkeypatch):
    from airunner_services.llm.managers.agent.mixins import rag_indexing_mixin

    rag, document, index_dir = _make_rag(tmp_path, monkeypatch)
    monkeypatch.setattr(
        rag_indexing_mixin,
        "iter_document_batches_from_file",
        lambda *_args: iter([[Document(page_content="updated source")]]),
    )

    assert rag._index_or_reindex_document(document)

    assert DocumentVectorIndex.load(str(index_dir)).documents[0].page_content == "updated source"
    assert len(list(index_dir.parent.glob(index_dir.name + ".reindex-backup-*"))) == 1


def test_metadata_failure_restores_old_index_registry_and_database(
    tmp_path, monkeypatch
):
    from airunner_services.llm.managers.agent.mixins import rag_indexing_mixin

    rag, document, index_dir = _make_rag(
        tmp_path, monkeypatch, fail_registry=True
    )
    monkeypatch.setattr(
        rag_indexing_mixin,
        "iter_document_batches_from_file",
        lambda *_args: iter([[Document(page_content="rebuilt text")]]),
    )
    before_registry = Path(rag.registry_path).read_bytes()

    assert not rag._reindex_single_document(document)

    assert DocumentVectorIndex.load(str(index_dir)).documents[0].page_content == "old content"
    assert Path(rag.registry_path).read_bytes() == before_registry
    assert document.file_hash == "old-hash"
    assert document.indexed is True
    assert len(list(index_dir.parent.glob(index_dir.name + ".reindex-failed-*"))) == 1


def test_source_change_during_embedding_rejects_candidate_before_switch(
    tmp_path, monkeypatch
):
    from airunner_services.llm.managers.agent.mixins import rag_indexing_mixin

    rag, document, index_dir = _make_rag(tmp_path, monkeypatch)
    monkeypatch.setattr(
        rag_indexing_mixin,
        "iter_document_batches_from_file",
        lambda *_args: iter([[Document(page_content="candidate")]]),
    )
    original_registry = Path(rag.registry_path).read_bytes()
    observed = iter(("source-before", "source-after"))
    rag._calculate_file_hash = lambda _path: next(observed)

    assert not rag._reindex_single_document(document)

    assert DocumentVectorIndex.load(str(index_dir)).documents[0].page_content == "old content"
    assert Path(rag.registry_path).read_bytes() == original_registry
    assert not list(index_dir.parent.glob(index_dir.name + ".reindex-backup-*"))
