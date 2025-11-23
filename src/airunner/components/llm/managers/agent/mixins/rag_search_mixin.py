"""RAG Search functionality.

This module provides the search and retrieval interface for the RAG system,
used by LangChain tools to query documents.
"""

from typing import List, Optional, Any
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores.types import (
    MetadataFilters,
    ExactMatchFilter,
)
from llama_index.core.schema import QueryBundle
from langchain_core.documents import Document


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
            query_bundle = QueryBundle(query_str=query)
            nodes = self.retriever.retrieve(query_bundle)

            self.logger.debug(f"Retrieved {len(nodes)} nodes from retriever")

            # Convert LlamaIndex nodes to LangChain-style documents
            results = []
            for i, node_with_score in enumerate(
                nodes[:k]
            ):  # Limit to k results
                try:
                    # NodeWithScore has a .node property containing the actual BaseNode
                    # Try different ways to get the text content
                    text = None
                    node = None

                    # First get the underlying node
                    if hasattr(node_with_score, "node"):
                        node = node_with_score.node
                    else:
                        # It might already be a node
                        node = node_with_score

                    # Now try to get text from the node
                    # Check both existence AND non-emptiness
                    if hasattr(node, "text") and node.text:
                        text = node.text
                    elif hasattr(node, "get_text"):
                        text = node.get_text()
                    elif hasattr(node, "get_content"):
                        text = node.get_content()

                    # Get metadata
                    metadata = {}
                    if hasattr(node, "metadata") and node.metadata:
                        metadata = node.metadata

                    self.logger.debug(
                        f"Node {i+1}: type={type(node_with_score).__name__}, "
                        f"node_type={type(node).__name__ if node else 'None'}, "
                        f"text_len={len(text) if text else 0}, "
                        f"has_metadata={bool(metadata)}"
                    )

                    if not text:
                        self.logger.warning(
                            f"Node {i+1} has no text content. "
                            f"Node attrs: {[attr for attr in dir(node) if not attr.startswith('_')][:15]}"
                        )

                    doc = Document(
                        page_content=text or "",
                        metadata=metadata,
                    )
                    results.append(doc)

                except Exception as e:
                    self.logger.error(f"Error processing node {i+1}: {e}")
                    continue

            self.logger.info(
                f"Search for '{query[:100]}' returned {len(results)} results, "
                f"{sum(1 for r in results if r.page_content)} with content"
            )

            return results

        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            return []

    def get_retriever_for_query(
        self,
        query: str,
        similarity_top_k: int = 5,
        doc_ids: Optional[List[str]] = None,
    ) -> Optional[VectorIndexRetriever]:
        """Get a context-aware retriever for a specific query.

        Args:
            query: The user's query
            similarity_top_k: Number of chunks to retrieve
            doc_ids: Optional list of specific document IDs to search within

        Returns:
            Configured retriever with optional metadata filters
        """
        if not self.index:
            self.logger.error("No index available for retriever")
            return None

        try:
            filters = None
            if doc_ids:
                filters = MetadataFilters(
                    filters=[
                        ExactMatchFilter(key="doc_id", value=doc_id)
                        for doc_id in doc_ids
                    ]
                )

            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=similarity_top_k,
                filters=filters,
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
    def retriever(self) -> Optional[VectorIndexRetriever]:
        """Get retriever for search operations.

        Priority order:
        1. Multi-index retriever for active documents (if any exist in database)
        2. Unified index retriever (for dynamically loaded content)
        3. None (no documents available)

        Returns:
            VectorIndexRetriever instance or None
        """
        if not self._retriever:
            # Try creating multi-index retriever for active documents
            active_doc_ids = self._get_active_document_ids()
            if active_doc_ids and len(active_doc_ids) > 0:
                # Have active documents in database - use multi-index retriever
                try:
                    from airunner.components.llm.managers.agent.retriever import (
                        MultiIndexRetriever,
                    )

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
                # No active documents, but unified index exists (dynamically loaded content)
                try:
                    self._retriever = VectorIndexRetriever(
                        index=self._index,
                        similarity_top_k=5,
                    )
                    self.logger.debug(
                        "Created retriever for unified index (dynamically loaded content)"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error creating unified index retriever: {e}"
                    )
            else:
                # No documents available
                self.logger.debug("No documents available for retriever")

        return self._retriever
