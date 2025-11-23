"""Multi-Index Retriever for RAG system.

This module provides lazy-loading retrieval across multiple per-document indexes.
Only documents marked as active in the database are loaded and searched.
"""

from typing import List
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import QueryBundle, NodeWithScore
from llama_index.core.retrievers import VectorIndexRetriever


class MultiIndexRetriever(BaseRetriever):
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

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Load and search only documents marked as active by user.

        This searches both:
        1. Per-document persistent indexes (from database documents)
        2. Unified in-memory index (from files loaded via ensure_indexed_files)

        Args:
            query_bundle: Query to execute

        Returns:
            List of scored nodes from all active document indexes
        """
        all_nodes = []

        # First, search the unified in-memory index if it exists
        # This contains files loaded via ensure_indexed_files() or load_file_into_rag()
        if hasattr(self._rag_mixin, "_index") and self._rag_mixin._index:
            try:
                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.debug(
                        "Searching unified in-memory index"
                    )

                unified_retriever = VectorIndexRetriever(
                    index=self._rag_mixin._index,
                    similarity_top_k=self._similarity_top_k,
                )
                unified_nodes = unified_retriever.retrieve(query_bundle)
                all_nodes.extend(unified_nodes)

                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.debug(
                        f"Found {len(unified_nodes)} nodes from unified index"
                    )

            except Exception as e:
                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.error(
                        f"Error retrieving from unified index: {e}"
                    )

        # Then search per-document persistent indexes
        active_doc_ids = self._rag_mixin._get_active_document_ids()

        if not active_doc_ids:
            if hasattr(self._rag_mixin, "logger"):
                self._rag_mixin.logger.warning(
                    "No active documents selected. Please activate documents in the Documents panel."
                )
            # If we have unified index results, return those
            if all_nodes:
                all_nodes.sort(key=lambda x: x.score or 0.0, reverse=True)
                return all_nodes[: self._similarity_top_k]
            return []

        if hasattr(self._rag_mixin, "logger"):
            self._rag_mixin.logger.info(
                f"Searching {len(active_doc_ids)} active document(s)"
            )

        for doc_id in active_doc_ids:
            try:
                # Lazy load the index
                doc_index = self._rag_mixin._load_doc_index(doc_id)
                if not doc_index:
                    continue

                # Create a retriever for this specific index
                retriever = VectorIndexRetriever(
                    index=doc_index,
                    similarity_top_k=self._similarity_top_k,
                )

                # Retrieve nodes from this index
                nodes = retriever.retrieve(query_bundle)
                all_nodes.extend(nodes)

            except Exception as e:
                # Log but continue with other indexes
                if hasattr(self._rag_mixin, "logger"):
                    self._rag_mixin.logger.error(
                        f"Error retrieving from index {doc_id}: {e}"
                    )

        # Sort all nodes by score (highest first)
        all_nodes.sort(key=lambda x: x.score or 0.0, reverse=True)

        # Return top N nodes across all filtered indexes
        return all_nodes[: self._similarity_top_k]
