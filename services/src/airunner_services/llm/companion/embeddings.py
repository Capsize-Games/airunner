"""Local embedding index with explicit index identity (release B04).

Adapts the selected local embedding runtime (Intfloat E5 Large,
``intfloat/e5-large`` — see ``model_bootstrap_data.py`` and the R02
manifest ``release-planning/linux-v1/hardware-models.md`` §2) to the
B01 companion contracts. Every persisted index records the embedding
model identity it was built with (model id, revision, dimension); an
index is only ever searched with a client whose identity matches it
exactly. A model/revision/dimension change never yields mixed-space
search results — it raises ``CompanionError`` with
``ERROR_EMBEDDING_SPACE_MISMATCH`` and, via
``open_companion_index``, schedules one explicit
``CompanionJobType.EMBEDDING_REBUILD`` job instead.

Deliberately local-only: this module performs no downloads, no model
loading, and no network calls. It embeds through an injected
``CompanionEmbeddingClient`` (the real one is adapted in
``airunner_services.runtimes.local_embeddings``) and persists to a
caller-chosen directory (JSON manifest + ``embeddings.npy``, the same
on-disk shape as the existing RAG ``DocumentVectorIndex``).

Import this submodule directly; it is not re-exported from the
``companion`` package ``__init__`` (numpy), mirroring
``repository.py``/``jobs.py``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import numpy as np
from pydantic import BaseModel

from .contracts import (
    ERROR_EMBEDDING_SPACE_MISMATCH,
    ChatbotId,
    CompanionError,
    CompanionErrorCode,
    SessionId,
)
from .scheduler import (
    CompanionJobRequest,
    CompanionJobType,
    CompanionScheduler,
)
from airunner_services.runtimes.embedding_contracts import EmbeddingModelIdentity

EMBEDDING_INDEX_SCHEMA_VERSION = 1
INDEX_MANIFEST_FILE = "companion_index.json"
INDEX_EMBEDDINGS_FILE = "embeddings.npy"


@runtime_checkable
class CompanionEmbeddingClient(Protocol):
    """Embeds text into one explicit, local embedding space."""

    @property
    def identity(self) -> EmbeddingModelIdentity:
        """The space this client embeds into. Never inferred."""
        ...

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed indexable texts; one vector per text, in order."""
        ...

    def embed_query(self, text: str) -> List[float]:
        """Embed one search query."""
        ...


@dataclass(slots=True)
class ScoredMemoryText:
    """One index hit with cosine similarity score."""

    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompanionEmbeddingIndex:
    """One chatbot's in-memory embedding index plus its identity.

    Vectors are L2-normalized at add time so search is a single
    matrix product. Every entry point re-checks identity: adding or
    searching with a client from another space, or loading a
    manifest written by one, raises instead of mixing spaces.
    """

    def __init__(
        self,
        identity: EmbeddingModelIdentity,
        texts: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[np.ndarray] = None,
    ) -> None:
        self._identity = identity
        self._texts = list(texts or [])
        self._metadatas = list(metadatas) if metadatas is not None else [{} for _ in self._texts]
        self._embeddings = _as_matrix(embeddings)
        if len(self._texts) != len(self._metadatas) or len(self._texts) != self._embeddings.shape[0]:
            raise ValueError("embedding index rows are misaligned")
        if any(not isinstance(metadata, dict) for metadata in self._metadatas):
            raise ValueError("embedding metadata must contain dictionaries")
        if self._embeddings.size and self._embeddings.shape[1] != int(
            identity.dimension
        ):
            raise _mismatch(identity, f"dim={self._embeddings.shape[1]}")

    @property
    def identity(self) -> EmbeddingModelIdentity:
        return self._identity

    def __len__(self) -> int:
        return len(self._texts)

    def add_texts(
        self,
        texts: List[str],
        client: CompanionEmbeddingClient,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Embed and append texts; rejects a foreign-space client."""
        self._require_identity(client)
        metadata_rows = list(metadatas) if metadatas is not None else [{} for _ in texts]
        if len(metadata_rows) != len(texts) or any(
            not isinstance(metadata, dict) for metadata in metadata_rows
        ):
            raise ValueError("embedding metadata must match the input texts")
        if not texts:
            return
        vectors = [
            self._require_vector(row) for row in client.embed_documents(texts)
        ]
        if len(vectors) != len(texts):
            raise CompanionError(
                CompanionErrorCode(code=ERROR_EMBEDDING_SPACE_MISMATCH)
            )
        matrix = _normalize_rows(np.asarray(vectors, dtype=np.float32))
        updated = matrix if self._embeddings.size == 0 else np.vstack((self._embeddings, matrix))
        self._texts.extend(texts)
        self._metadatas.extend(metadata_rows)
        self._embeddings = updated

    def search(
        self,
        query: str,
        client: CompanionEmbeddingClient,
        k: int,
    ) -> List[ScoredMemoryText]:
        """Return up to ``k`` hits; never searches across spaces."""
        self._require_identity(client)
        if k <= 0 or not self._texts or self._embeddings.size == 0:
            return []
        vector = _normalize_vector(
            np.asarray(self._require_vector(client.embed_query(query)))
        )
        scores = self._embeddings @ vector
        ranked = np.argsort(scores)[::-1][:k]
        return [
            ScoredMemoryText(
                text=self._texts[item],
                score=float(scores[item]),
                metadata=dict(self._metadatas[item]),
            )
            for item in ranked
        ]

    def save(self, persist_dir: str) -> None:
        """Persist identity, texts, and vectors to ``persist_dir``."""
        os.makedirs(persist_dir, exist_ok=True)
        manifest = {
            "schema_version": EMBEDDING_INDEX_SCHEMA_VERSION,
            "identity": self._identity.model_dump(),
            "texts": self._texts,
            "metadatas": self._metadatas,
        }
        with open(_manifest_path(persist_dir), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False)
        np.save(_embeddings_path(persist_dir), self._embeddings)

    @classmethod
    def load(
        cls, persist_dir: str, client: CompanionEmbeddingClient
    ) -> "CompanionEmbeddingIndex":
        """Load a persisted index; rejects a foreign-space manifest."""
        with open(_manifest_path(persist_dir), "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        stored = EmbeddingModelIdentity(**manifest["identity"])
        if not stored.matches(client.identity):
            raise _mismatch(client.identity, _describe(stored))
        embeddings = np.load(_embeddings_path(persist_dir))
        return cls(
            identity=stored,
            texts=list(manifest["texts"]),
            metadatas=list(manifest["metadatas"]),
            embeddings=embeddings,
        )

    @classmethod
    def is_persisted(cls, persist_dir: str) -> bool:
        """Return whether a persisted index exists on disk."""
        return os.path.exists(_manifest_path(persist_dir)) and os.path.exists(
            _embeddings_path(persist_dir)
        )

    def _require_identity(self, client: CompanionEmbeddingClient) -> None:
        if not self._identity.matches(client.identity):
            raise _mismatch(self._identity, _describe(client.identity))

    def _require_vector(self, vector: List[float]) -> List[float]:
        if len(vector) != int(self._identity.dimension):
            raise _mismatch(self._identity, f"dim={len(vector)}")
        return [float(value) for value in vector]


def open_companion_index(
    persist_dir: str,
    chatbot_id: ChatbotId,
    client: CompanionEmbeddingClient,
    scheduler: CompanionScheduler,
    *,
    idempotency_key: str,
    session_id: Optional[SessionId] = None,
) -> CompanionEmbeddingIndex:
    """Load the persisted index, or start (and schedule) honestly.

    Returns a fresh empty index when nothing is persisted. When the
    persisted index belongs to another embedding space, schedules one
    explicit ``EMBEDDING_REBUILD`` job (idempotent on
    ``idempotency_key``) and re-raises the mismatch — the caller gets
    a scheduled rebuild, never mixed-space search results.
    """
    if not CompanionEmbeddingIndex.is_persisted(persist_dir):
        return CompanionEmbeddingIndex(identity=client.identity)
    try:
        return CompanionEmbeddingIndex.load(persist_dir, client)
    except CompanionError as exc:
        if exc.error.code != ERROR_EMBEDDING_SPACE_MISMATCH:
            raise
        scheduler.schedule(
            CompanionJobRequest(
                job_type=CompanionJobType.EMBEDDING_REBUILD,
                chatbot_id=chatbot_id,
                session_id=session_id,
                idempotency_key=idempotency_key,
                payload={
                    "persist_dir": persist_dir,
                    "identity": client.identity.model_dump(),
                },
            )
        )
        raise


def rebuild_companion_index(
    persist_dir: str, client: CompanionEmbeddingClient
) -> CompanionEmbeddingIndex:
    """Re-embed the persisted texts with ``client`` and re-save.

    This is the operation a B06 ``EMBEDDING_REBUILD`` handler runs:
    the manifest keeps the raw texts, so a space change does not
    lose the indexed content — it only requires re-embedding it.
    """
    with open(_manifest_path(persist_dir), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    rebuilt = CompanionEmbeddingIndex(identity=client.identity)
    rebuilt.add_texts(
        list(manifest["texts"]),
        client,
        metadatas=list(manifest["metadatas"]),
    )
    rebuilt.save(persist_dir)
    return rebuilt


def _mismatch(expected: EmbeddingModelIdentity, found: str) -> CompanionError:
    return CompanionError(
        CompanionErrorCode(
            code=ERROR_EMBEDDING_SPACE_MISMATCH,
            detail=f"expected {_describe(expected)}, found {found}",
        )
    )


def _describe(identity: EmbeddingModelIdentity) -> str:
    return (
        f"{identity.model_id}@{identity.revision} " f"dim={identity.dimension}"
    )


def _manifest_path(persist_dir: str) -> str:
    return os.path.join(persist_dir, INDEX_MANIFEST_FILE)


def _embeddings_path(persist_dir: str) -> str:
    return os.path.join(persist_dir, INDEX_EMBEDDINGS_FILE)


def _as_matrix(embeddings: Optional[np.ndarray]) -> np.ndarray:
    if embeddings is None:
        return np.zeros((0, 0), dtype=np.float32)
    matrix = np.asarray(embeddings, dtype=np.float32)
    if matrix.size == 0:
        return np.zeros((0, 0), dtype=np.float32)
    if matrix.ndim == 1:
        return matrix.reshape(1, -1)
    return matrix


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return vector
    return vector / norm


__all__ = [
    "EMBEDDING_INDEX_SCHEMA_VERSION",
    "INDEX_EMBEDDINGS_FILE",
    "INDEX_MANIFEST_FILE",
    "CompanionEmbeddingClient",
    "CompanionEmbeddingIndex",
    "EmbeddingModelIdentity",
    "ScoredMemoryText",
    "open_companion_index",
    "rebuild_companion_index",
]
