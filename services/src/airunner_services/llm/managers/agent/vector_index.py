"""Lightweight persisted vector index for LangChain-native RAG."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import numpy as np
from langchain_core.documents import Document


DOCUMENTS_FILE = "documents.json"
EMBEDDINGS_FILE = "embeddings.npy"
IDENTITY_FILE = "embedding_identity.json"


class EmbeddingIdentityMismatchError(ValueError):
    """Index vectors are legacy or belong to a different embedding space."""


@dataclass(slots=True)
class ScoredDocument:
    """Document search hit with similarity score."""

    document: Document
    score: float


class DocumentVectorIndex:
    """Persisted cosine-similarity index for LangChain documents."""

    def __init__(
        self,
        documents: Optional[Sequence[Document]] = None,
        embeddings: Optional[np.ndarray] = None,
        embedding_identity: Optional[dict[str, Any]] = None,
    ):
        self.documents = list(documents or [])
        self.embeddings = _as_matrix(embeddings)
        self.embedding_identity = embedding_identity
        self._validate_alignment()

    @classmethod
    def from_documents(
        cls,
        documents: Sequence[Document],
        embedding_model: Any,
        text_splitter: Any,
    ) -> "DocumentVectorIndex":
        chunks = _chunk_documents(documents, text_splitter)
        embeddings = _embed_documents(chunks, embedding_model)
        identity = _identity_record(embedding_model)
        return cls(chunks, embeddings, identity)

    @classmethod
    def load(cls, persist_dir: str) -> "DocumentVectorIndex":
        payload = _load_payload(persist_dir)
        documents = [_payload_to_document(item) for item in payload]
        embeddings = np.load(_embeddings_path(persist_dir), allow_pickle=False)
        identity_path = _identity_path(persist_dir)
        identity = None
        if os.path.exists(identity_path):
            with open(identity_path, "r", encoding="utf-8") as file:
                identity = json.load(file)
            _validate_identity_record(identity)
        return cls(documents, embeddings, identity)

    @classmethod
    def is_persisted(cls, persist_dir: str) -> bool:
        """Return whether a persisted index exists on disk."""
        return os.path.exists(_documents_path(persist_dir)) and os.path.exists(
            _embeddings_path(persist_dir)
        )

    def add_documents(
        self,
        documents: Sequence[Document],
        embedding_model: Any,
        text_splitter: Any,
    ) -> None:
        chunks = _chunk_documents(documents, text_splitter)
        if not chunks:
            return
        embeddings = _embed_documents(chunks, embedding_model)
        identity = _identity_record(embedding_model)
        if self.documents or self.embeddings.size:
            if self.embedding_identity is not None and identity is None:
                raise EmbeddingIdentityMismatchError(
                    "active embedder has no verified identity; reindex required"
                )
            _require_compatible_identity(self.embedding_identity, identity)
        combined = _combine_embeddings(self.embeddings, embeddings)
        self.documents.extend(chunks)
        self.embeddings = combined
        if self.embedding_identity is None:
            self.embedding_identity = identity

    def similarity_search(
        self,
        query: str,
        embedding_model: Any,
        k: int,
        doc_ids: Optional[Sequence[str]] = None,
        expected_identity: Optional[dict[str, Any]] = None,
    ) -> list[ScoredDocument]:
        actual_identity = _identity_record(embedding_model)
        if expected_identity is not None and expected_identity != actual_identity:
            raise EmbeddingIdentityMismatchError(
                "query embedder identity differs from requested identity"
            )
        expected_identity = actual_identity
        _require_compatible_identity(self.embedding_identity, expected_identity)
        query_vector = embedding_model.embed_query(query)
        return self.similarity_search_by_vector(
            query_vector, k, doc_ids, expected_identity
        )

    def similarity_search_by_vector(
        self,
        query_vector: Sequence[float],
        k: int,
        doc_ids: Optional[Sequence[str]] = None,
        expected_identity: Optional[dict[str, Any]] = None,
    ) -> list[ScoredDocument]:
        _require_compatible_identity(self.embedding_identity, expected_identity)
        if not self.documents or self.embeddings.size == 0:
            return []
        query = np.asarray(query_vector, dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != self.embeddings.shape[1]:
            raise ValueError("query vector dimension does not match index")
        if self.embedding_identity is not None and query.shape[0] != self.embedding_identity["dimension"]:
            raise ValueError("query vector dimension does not match index identity")
        indices = _matching_indices(self.documents, doc_ids)
        if not indices:
            return []
        return _rank_documents(
            self.documents,
            self.embeddings,
            query,
            indices,
            k,
        )

    def persist(self, persist_dir: str) -> None:
        """Persist documents and embeddings to disk."""
        self._validate_alignment()
        if self.embedding_identity is None and os.path.exists(_identity_path(persist_dir)):
            raise EmbeddingIdentityMismatchError(
                "refusing to overwrite an identity-bearing index without its identity"
            )
        os.makedirs(persist_dir, exist_ok=True)
        payload = [_document_to_payload(doc) for doc in self.documents]
        with open(_documents_path(persist_dir), "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False, default=str)
        np.save(_embeddings_path(persist_dir), self.embeddings)
        if self.embedding_identity is not None:
            with open(_identity_path(persist_dir), "w", encoding="utf-8") as file:
                json.dump(self.embedding_identity, file, indent=2, sort_keys=True)

    def replace_persisted_atomically(self, persist_dir: str) -> Optional[str]:
        """Validate this complete E5 index, then replace an index directory.

        Candidate files are first written to a sibling staging directory and
        reloaded for validation. An existing index is retained in a uniquely
        named sibling backup. If promotion fails, the old directory is
        restored. Staging and backup directories are intentionally retained
        for recovery and inspection.
        """
        self._validate_alignment()
        if self.embedding_identity is None:
            raise EmbeddingIdentityMismatchError(
                "staged reindex requires a verified embedding identity"
            )

        target = os.path.abspath(persist_dir)
        parent = os.path.dirname(target)
        os.makedirs(parent, exist_ok=True)
        if os.path.islink(target):
            raise ValueError("refusing to replace a symlinked index directory")
        if os.path.lexists(target) and not os.path.isdir(target):
            raise ValueError("index replacement target is not a directory")

        stage = tempfile.mkdtemp(
            prefix=f".{os.path.basename(target)}.reindex-stage-", dir=parent
        )
        self.persist(stage)
        _validate_staged_index(self, stage)

        backup = None
        if os.path.lexists(target):
            backup = f"{target}.reindex-backup-{uuid.uuid4().hex}"
            os.replace(target, backup)
        try:
            os.replace(stage, target)
            _validate_staged_index(self, target)
        except Exception:
            try:
                if os.path.lexists(target):
                    failed = f"{target}.reindex-failed-{uuid.uuid4().hex}"
                    os.replace(target, failed)
            finally:
                if backup is not None and os.path.lexists(backup):
                    os.replace(backup, target)
            raise
        return backup

    @staticmethod
    def restore_persisted_backup(persist_dir: str, backup_dir: str) -> str:
        """Restore a retained backup and quarantine the failed replacement."""
        target = os.path.abspath(persist_dir)
        backup = os.path.abspath(backup_dir)
        if os.path.dirname(target) != os.path.dirname(backup):
            raise ValueError("index backup must be a sibling directory")
        if not os.path.isdir(backup):
            raise ValueError("index backup directory is unavailable")
        failed = f"{target}.reindex-failed-{uuid.uuid4().hex}"
        if os.path.lexists(target):
            os.replace(target, failed)
        os.replace(backup, target)
        return failed

    def _validate_alignment(self) -> None:
        if self.embeddings.ndim != 2 or self.embeddings.shape[0] != len(self.documents):
            raise ValueError("document and embedding row counts do not match")
        if self.embedding_identity is not None:
            _validate_identity_record(self.embedding_identity)
            if self.embeddings.size and self.embeddings.shape[1] != self.embedding_identity["dimension"]:
                raise ValueError("embedding dimension does not match index identity")


def _chunk_documents(documents: Sequence[Document], text_splitter: Any) -> list[Document]:
    chunks = text_splitter.split_documents(list(documents))
    return [chunk for chunk in chunks if chunk.page_content.strip()]


def _embed_documents(documents: Sequence[Document], embedding_model: Any) -> np.ndarray:
    if not documents:
        return np.zeros((0, 0), dtype=np.float32)
    texts = [document.page_content for document in documents]
    vectors = np.asarray(embedding_model.embed_documents(texts), dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(texts):
        raise ValueError("embedding provider returned an invalid document batch")
    identity = _identity_record(embedding_model)
    if identity is not None and vectors.shape[1] != identity["dimension"]:
        raise ValueError("embedding dimension does not match verified identity")
    return _normalize_rows(vectors)


def _identity_record(embedding_model: Any) -> Optional[dict[str, Any]]:
    identity = getattr(embedding_model, "verified_identity", None)
    return identity.to_dict() if callable(getattr(identity, "to_dict", None)) else None


def _validate_identity_record(identity: Any) -> None:
    from airunner_services.runtimes.e5_model_identity import E5ModelIdentity

    if not isinstance(identity, dict):
        raise EmbeddingIdentityMismatchError("invalid embedding identity; reindex required")
    try:
        E5ModelIdentity.from_dict(identity)
    except ValueError as exc:
        raise EmbeddingIdentityMismatchError(
            "invalid embedding identity; reindex required"
        ) from exc


def _require_compatible_identity(
    stored: Optional[dict[str, Any]], expected: Optional[dict[str, Any]]
) -> None:
    if expected is None:
        if stored is not None:
            raise EmbeddingIdentityMismatchError(
                "query has no verified embedding identity"
            )
        return
    _validate_identity_record(expected)
    if stored is None:
        raise EmbeddingIdentityMismatchError(
            "index has no verified embedding identity; reindex required"
        )
    _validate_identity_record(stored)
    if stored != expected:
        raise EmbeddingIdentityMismatchError(
            "index embedding identity differs from the active model; reindex required"
        )


def _combine_embeddings(current: np.ndarray, new: np.ndarray) -> np.ndarray:
    if current.size == 0:
        return new
    if new.size == 0:
        return current
    return np.vstack((current, new))


def _matching_indices(
    documents: Sequence[Document],
    doc_ids: Optional[Sequence[str]],
) -> list[int]:
    if not doc_ids:
        return list(range(len(documents)))
    return [
        index
        for index, document in enumerate(documents)
        if document.metadata.get("doc_id") in set(doc_ids)
    ]


def _rank_documents(
    documents: Sequence[Document],
    embeddings: np.ndarray,
    query_vector: np.ndarray,
    indices: Sequence[int],
    k: int,
) -> list[ScoredDocument]:
    normalized_query = _normalize_vector(query_vector)
    subset = embeddings[list(indices)]
    scores = subset @ normalized_query
    ranked = np.argsort(scores)[::-1][:k]
    return [
        ScoredDocument(documents[indices[item]], float(scores[item]))
        for item in ranked
    ]


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix.reshape(0, 0)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return vector
    return vector / norm


def _as_matrix(embeddings: Optional[np.ndarray]) -> np.ndarray:
    if embeddings is None:
        return np.zeros((0, 0), dtype=np.float32)
    matrix = np.asarray(embeddings, dtype=np.float32)
    if matrix.size == 0:
        return np.zeros((0, 0), dtype=np.float32)
    if matrix.ndim == 1:
        return matrix.reshape(1, -1)
    return matrix


def _document_to_payload(document: Document) -> dict[str, Any]:
    return {
        "page_content": document.page_content,
        "metadata": document.metadata,
    }


def _payload_to_document(payload: dict[str, Any]) -> Document:
    return Document(
        page_content=payload.get("page_content", ""),
        metadata=payload.get("metadata", {}),
    )


def _load_payload(persist_dir: str) -> list[dict[str, Any]]:
    with open(_documents_path(persist_dir), "r", encoding="utf-8") as file:
        return json.load(file)


def _documents_path(persist_dir: str) -> str:
    return os.path.join(persist_dir, DOCUMENTS_FILE)


def _embeddings_path(persist_dir: str) -> str:
    return os.path.join(persist_dir, EMBEDDINGS_FILE)


def _identity_path(persist_dir: str) -> str:
    return os.path.join(persist_dir, IDENTITY_FILE)


def _validate_staged_index(expected: DocumentVectorIndex, path: str) -> None:
    actual = DocumentVectorIndex.load(path)
    expected_payload = json.loads(
        json.dumps(
            [_document_to_payload(doc) for doc in expected.documents],
            ensure_ascii=False,
            default=str,
        )
    )
    actual_payload = [_document_to_payload(doc) for doc in actual.documents]
    if actual_payload != expected_payload:
        raise ValueError("staged index document payload changed during persistence")
    if actual.embedding_identity != expected.embedding_identity:
        raise ValueError("staged index embedding identity changed during persistence")
    if not np.array_equal(actual.embeddings, expected.embeddings):
        raise ValueError("staged index vectors changed during persistence")
