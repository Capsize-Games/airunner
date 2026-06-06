"""RAG search functionality."""

from typing import List, Optional, Any


from airunner_services.llm.managers.agent.retriever import (
    DocumentIndexRetriever,
    MultiIndexRetriever,
)


class RAGSearchMixin:
    """Search and retrieval operations for RAG system.

    Provides the main search interface used by rag_tools.py to query
    documents. Uses MultiIndexRetriever for lazy loading of active documents.
    """

    def search(self, query: str, k: int = 3) -> List[Any]:
        """Search for relevant documents using the retriever.

        This is the main search method used by rag_tools.py.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of Document objects with page_content and metadata
        """
        if not self.retriever:
            self.logger.warning("No retriever available for search")
            return []

        try:
            results = self.retriever.retrieve(query)

            self.logger.info(
                f"Search for '{query[:100]}' returned {len(results)} results, "
                f"{sum(1 for r in results if r.page_content)} with content"
            )

            return results[:k]

        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            return []

    def get_retriever_for_query(
        self,
        query: str,
        similarity_top_k: int = 5,
        doc_ids: Optional[List[str]] = None,
    ) -> Optional[DocumentIndexRetriever]:
        """Get a context-aware retriever for a specific query.

        Args:
            query: The user's query
            similarity_top_k: Number of chunks to retrieve
            doc_ids: Optional list of specific document IDs to search within

        Returns:
            Configured retriever with optional metadata filters
        """
        if not self._index:
            self.logger.error("No index available for retriever")
            return None

        try:
            retriever = DocumentIndexRetriever(
                index=self._index,
                embedding_model=self.embedding,
                similarity_top_k=similarity_top_k,
                doc_ids=doc_ids,
            )

            self.logger.debug(
                f"Created retriever with top_k={similarity_top_k}, "
                f"filtered_docs={len(doc_ids) if doc_ids else 'all'}"
            )
            return retriever

        except Exception as e:
            self.logger.error(f"Error creating retriever: {e}")
            return None

    @property
    def retriever(self) -> Optional[Any]:
        """Get retriever for search operations.

        Priority order:
        1. Multi-index retriever for active documents (if any exist in database)
        2. Unified index retriever (for dynamically loaded content)
        3. None (no documents available)

        Returns:
            VectorIndexRetriever instance or None
        """
        if not self._retriever:
            active_doc_ids = self._get_active_document_ids()
            if active_doc_ids and len(active_doc_ids) > 0:
                try:
                    self._retriever = MultiIndexRetriever(
                        rag_mixin=self,
                        similarity_top_k=5,
                    )
                    self.logger.debug(
                        f"Created retriever for {len(active_doc_ids)} active document(s)"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error creating multi-index retriever: {e}"
                    )
            elif self._index:
                try:
                    self._retriever = DocumentIndexRetriever(
                        index=self._index,
                        embedding_model=self.embedding,
                        similarity_top_k=5,
                    )
                    self.logger.debug(
                        "Created retriever for unified index (dynamically loaded content)"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error creating unified index retriever: {e}"
                    )

        return self._retriever
