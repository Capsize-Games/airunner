"""Lightweight persisted vector index for LangChain-native RAG."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import numpy as np
from langchain_core.documents import Document


DOCUMENTS_FILE = "documents.json"
EMBEDDINGS_FILE = "embeddings.npy"


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
    ):
        self.documents = list(documents or [])
        self.embeddings = _as_matrix(embeddings)

    @classmethod
    def from_documents(
        cls,
        documents: Sequence[Document],
        embedding_model: Any,
        text_splitter: Any,
    ) -> "DocumentVectorIndex":
        chunks = _chunk_documents(documents, text_splitter)
        embeddings = _embed_documents(chunks, embedding_model)
        return cls(chunks, embeddings)

    @classmethod
    def load(cls, persist_dir: str) -> "DocumentVectorIndex":
        payload = _load_payload(persist_dir)
        documents = [_payload_to_document(item) for item in payload]
        embeddings = np.load(_embeddings_path(persist_dir), allow_pickle=False)
        return cls(documents, embeddings)

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
        self.documents.extend(chunks)
        self.embeddings = _combine_embeddings(self.embeddings, embeddings)

    def similarity_search(
        self,
        query: str,
        embedding_model: Any,
        k: int,
        doc_ids: Optional[Sequence[str]] = None,
    ) -> list[ScoredDocument]:
        query_vector = embedding_model.embed_query(query)
        return self.similarity_search_by_vector(query_vector, k, doc_ids)

    def similarity_search_by_vector(
        self,
        query_vector: Sequence[float],
        k: int,
        doc_ids: Optional[Sequence[str]] = None,
    ) -> list[ScoredDocument]:
        if not self.documents or self.embeddings.size == 0:
            return []
        indices = _matching_indices(self.documents, doc_ids)
        if not indices:
            return []
        return _rank_documents(
            self.documents,
            self.embeddings,
            np.asarray(query_vector, dtype=np.float32),
            indices,
            k,
        )

    def persist(self, persist_dir: str) -> None:
        """Persist documents and embeddings to disk."""
        os.makedirs(persist_dir, exist_ok=True)
        payload = [_document_to_payload(doc) for doc in self.documents]
        with open(_documents_path(persist_dir), "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False, default=str)
        np.save(_embeddings_path(persist_dir), self.embeddings)


def _chunk_documents(documents: Sequence[Document], text_splitter: Any) -> list[Document]:
    chunks = text_splitter.split_documents(list(documents))
    return [chunk for chunk in chunks if chunk.page_content.strip()]


def _embed_documents(documents: Sequence[Document], embedding_model: Any) -> np.ndarray:
    if not documents:
        return np.zeros((0, 0), dtype=np.float32)
    texts = [document.page_content for document in documents]
    return _normalize_rows(np.asarray(embedding_model.embed_documents(texts), dtype=np.float32))


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