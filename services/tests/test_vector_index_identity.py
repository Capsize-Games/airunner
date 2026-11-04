"""Identity checks preserve legacy index data and block vector-space mixing."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from langchain_core.documents import Document
from pathlib import Path

from airunner_services.llm.managers.agent.vector_index import (
    EmbeddingIdentityMismatchError,
    DocumentVectorIndex,
)
from airunner_services.runtimes import e5_model_identity as identity_module
from airunner_services.runtimes.e5_model_identity import E5ModelIdentity


def _identity() -> E5ModelIdentity:
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
    def __init__(self, identity):
        self.verified_identity = identity

    def embed_query(self, _text):
        return [1.0] + [0.0] * (identity_module.E5_LARGE_DIMENSION - 1)

    def embed_documents(self, texts):
        return [self.embed_query("") for _ in texts]


class _Splitter:
    def split_documents(self, documents):
        return list(documents)


def test_identity_sidecar_roundtrip_and_mismatch(tmp_path):
    identity = _identity()
    model = _Embedder(identity)
    index = DocumentVectorIndex.from_documents(
        [Document(page_content="hello", metadata={"doc_id": "one"})],
        model,
        _Splitter(),
    )
    index.persist(str(tmp_path))
    loaded = DocumentVectorIndex.load(str(tmp_path))
    assert loaded.embedding_identity == identity.to_dict()
    assert loaded.similarity_search("hello", model, 1)

    other = replace(identity, prefix_policy="different-prefix-space")
    with pytest.raises(EmbeddingIdentityMismatchError, match="invalid embedding identity"):
        loaded.similarity_search("hello", _Embedder(other), 1)


def test_legacy_index_search_requests_reindex_without_modification(tmp_path):
    index = DocumentVectorIndex(
        [Document(page_content="legacy")], np.asarray([[1.0, 0.0]])
    )
    index.persist(str(tmp_path))
    documents_path = tmp_path / "documents.json"
    embeddings_path = tmp_path / "embeddings.npy"
    before = (documents_path.read_bytes(), embeddings_path.read_bytes())
    loaded = DocumentVectorIndex.load(str(tmp_path))

    with pytest.raises(EmbeddingIdentityMismatchError, match="reindex required"):
        loaded.similarity_search_by_vector(
            [1.0, 0.0], 1, expected_identity=_identity().to_dict()
        )

    assert (documents_path.read_bytes(), embeddings_path.read_bytes()) == before
    assert not (tmp_path / "embedding_identity.json").exists()


def test_staged_reindex_keeps_recoverable_backup(tmp_path):
    identity = _identity()
    old = DocumentVectorIndex(
        [Document(page_content="old", metadata={"source": "old"})],
        np.asarray([[1.0] + [0.0] * 1023], dtype=np.float32),
        identity.to_dict(),
    )
    target = tmp_path / "index"
    old.persist(str(target))
    candidate = DocumentVectorIndex(
        [Document(page_content="new", metadata={"source": "new"})],
        np.asarray([[0.0, 1.0] + [0.0] * 1022], dtype=np.float32),
        identity.to_dict(),
    )

    backup = candidate.replace_persisted_atomically(str(target))

    assert backup is not None
    assert Path(backup).is_dir()
    assert DocumentVectorIndex.load(backup).documents[0].page_content == "old"
    assert DocumentVectorIndex.load(str(target)).documents[0].page_content == "new"
    assert not list(tmp_path.glob(".index.reindex-stage-*"))


def test_staged_reindex_restores_old_index_when_promotion_fails(
    tmp_path, monkeypatch
):
    identity = _identity()
    old = DocumentVectorIndex(
        [Document(page_content="old")],
        np.asarray([[1.0] + [0.0] * 1023], dtype=np.float32),
        identity.to_dict(),
    )
    target = tmp_path / "index"
    old.persist(str(target))
    candidate = DocumentVectorIndex(
        [Document(page_content="new")],
        np.asarray([[0.0, 1.0] + [0.0] * 1022], dtype=np.float32),
        identity.to_dict(),
    )
    real_replace = __import__("os").replace

    def fail_stage_promotion(source, destination):
        if ".reindex-stage-" in str(source) and str(destination) == str(target):
            raise OSError("injected stage promotion failure")
        return real_replace(source, destination)

    monkeypatch.setattr("airunner_services.llm.managers.agent.vector_index.os.replace", fail_stage_promotion)
    with pytest.raises(OSError, match="injected"):
        candidate.replace_persisted_atomically(str(target))

    assert DocumentVectorIndex.load(str(target)).documents[0].page_content == "old"
    assert list(tmp_path.glob(".index.reindex-stage-*"))
