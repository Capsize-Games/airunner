"""Retriever helpers for LangChain-native RAG."""

from typing import Optional, Sequence

from langchain_core.documents import Document

from airunner.components.llm.managers.agent.vector_index import (
    DocumentVectorIndex,
)


class DocumentIndexRetriever:
    """Query a single vector index."""

    def __init__(
        self,
        index: DocumentVectorIndex,
        embedding_model,
        similarity_top_k: int = 5,
        doc_ids: Optional[Sequence[str]] = None,
    ):
        self._index = index
        self._embedding_model = embedding_model
        self._similarity_top_k = similarity_top_k
        self._doc_ids = doc_ids

    def retrieve(self, query: str) -> list[Document]:
        hits = self._index.similarity_search(
            query,
            self._embedding_model,
            self._similarity_top_k,
            self._doc_ids,
        )
        return [hit.document for hit in hits]


class MultiIndexRetriever:
    """Lazily load and search multiple per-document indexes.

    Only loads documents marked as active=True in the database.
    This is a simple manual system - no automatic filtering or ranking.
    Users manually control which documents to search via the Documents panel.
    """

    def __init__(
        self,
        rag_mixin,
        similarity_top_k: int = 5,
        **kwargs,
    ):
        """Initialize multi-index retriever.

        Args:
            rag_mixin: Reference to RAGMixin instance for loading indexes
            similarity_top_k: Number of nodes to retrieve total
        """
        self._rag_mixin = rag_mixin
        self._similarity_top_k = similarity_top_k

    def retrieve(self, query: str) -> list[Document]:
        """Load and search only documents marked as active by user.

        This searches both:
        1. Per-document persistent indexes (from database documents)
        2. Unified in-memory index (from files loaded via ensure_indexed_files)

        Args:
        Returns:
            List of LangChain documents from active document indexes
        """
        query_vector = self._embed_query(query)
        if query_vector is None:
            return []

        all_documents: list = []

        if hasattr(self._rag_mixin, "_index") and self._rag_mixin._index:
            try:
                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.debug(
                        "Searching unified in-memory index"
                    )

                ensure_current = getattr(
                    self._rag_mixin._index,
                    "ensure_current_embeddings",
                    None,
                )
                if callable(ensure_current):
                    ensure_current(self._rag_mixin.embedding)

                all_documents.extend(
                    self._rag_mixin._index.similarity_search_by_vector(
                        query_vector,
                        self._similarity_top_k,
                    )
                )

                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.debug(
                        "Searched unified in-memory index successfully"
                    )

            except Exception as e:
                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.error(
                        f"Error retrieving from unified index: {e}"
                    )

        active_doc_ids = self._rag_mixin._get_active_document_ids()

        if not active_doc_ids:
            if hasattr(self._rag_mixin, "logger"):
                self._rag_mixin.logger.warning(
                    "No active documents selected. Please activate documents in the Documents panel."
                )
            return _top_documents(all_documents, self._similarity_top_k)

        if hasattr(self._rag_mixin, "logger"):
            self._rag_mixin.logger.info(
                f"Searching {len(active_doc_ids)} active document(s)"
            )

        for doc_id in active_doc_ids:
            try:
                doc_index = self._rag_mixin._load_doc_index(doc_id)
                if not doc_index:
                    continue

                ensure_current = getattr(
                    doc_index,
                    "ensure_current_embeddings",
                    None,
                )
                if callable(ensure_current):
                    ensure_current(self._rag_mixin.embedding)

                all_documents.extend(
                    doc_index.similarity_search_by_vector(
                        query_vector,
                        self._similarity_top_k,
                    )
                )

            except Exception as e:
                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.error(
                        f"Error retrieving from index {doc_id}: {e}"
                    )

        return _top_documents(all_documents, self._similarity_top_k)

    def _embed_query(self, query: str):
        try:
            return self._rag_mixin.embedding.embed_query(query)
        except Exception as exc:
            if hasattr(self._rag_mixin, "logger"):
                self._rag_mixin.logger.error(
                    f"Error embedding query for retrieval: {exc}"
                )
            return None


def _top_documents(hits: list, limit: int) -> list[Document]:
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return [hit.document for hit in hits[:limit]]
