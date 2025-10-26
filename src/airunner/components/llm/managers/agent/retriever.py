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

        This is a simple manual system - no automatic filtering or ranking.
        Only documents with active=True in the database are loaded.

        Args:
            query_bundle: Query to execute

        Returns:
            List of scored nodes from all active document indexes
        """
        all_nodes = []

        # Get active document IDs from database
        active_doc_ids = self._rag_mixin._get_active_document_ids()

        if not active_doc_ids:
            if hasattr(self._rag_mixin, "logger"):
                self._rag_mixin.logger.warning(
                    "No active documents selected. Please activate documents in the Documents panel."
                )
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
