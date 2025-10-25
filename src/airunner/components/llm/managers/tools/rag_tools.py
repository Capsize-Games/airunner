"""RAG and document search tools."""

import os
import logging
from typing import Callable, Any, Optional

from langchain.tools import tool

from airunner.components.documents.data.models.document import Document
from airunner.components.data.session_manager import session_scope
from airunner.enums import SignalCode


class RAGTools:
    """Mixin class providing RAG and document search tools."""

    def rag_search_tool(self) -> Callable:
        """Retrieve relevant information from RAG documents."""

        @tool
        def rag_search(query: str) -> str:
            """Search through uploaded documents for relevant information.

            Args:
                query: Search query for finding relevant document content

            Returns:
                Relevant excerpts from documents or error message
            """
            if not self.rag_manager:
                return "RAG system not available"

            try:
                results = self.rag_manager.search(query, k=3)
                if not results:
                    return "No relevant information found in documents"

                context_parts = []
                for i, doc in enumerate(results, 1):
                    source = doc.metadata.get("source", "unknown")
                    content = (
                        doc.page_content[:500]
                        if len(doc.page_content) > 500
                        else doc.page_content
                    )
                    context_parts.append(f"[Source {i}]\n{content}")

                return "\n\n".join(context_parts)
            except Exception as e:
                return f"Error searching documents: {str(e)}"

        return rag_search

    def search_knowledge_base_documents_tool(self) -> Callable:
        """Search across all knowledge base documents to find relevant ones to load for RAG."""

        @tool
        def search_knowledge_base_documents(query: str, k: int = 10) -> str:
            """Search across ALL knowledge base documents to find the most relevant ones.

            This is a BROAD SEARCH across document titles and paths - like a search engine
            for your entire knowledge base. Use this BEFORE using rag_search to determine
            which documents should be loaded into RAG for detailed querying.

            The knowledge base may contain ebooks, PDFs, markdown files, ZIM files, and more.
            This tool helps you discover which documents are relevant to the user's question
            so you can load them for deeper analysis.

            Args:
                query: What topics/documents you're looking for (e.g., "Python programming books")
                k: Number of document paths to return (default 10)

            Returns:
                List of relevant document paths ranked by relevance

            Examples:
                search_knowledge_base_documents("machine learning tutorials")
                search_knowledge_base_documents("health and fitness guides", k=5)
                search_knowledge_base_documents("cooking recipes")
            """
            try:
                with session_scope() as session:
                    # Get all active documents
                    docs = session.query(Document).filter_by(active=True).all()

                    if not docs:
                        return "No documents found in knowledge base. Please index some documents first."

                    # Simple keyword-based relevance scoring
                    query_lower = query.lower()
                    query_terms = query_lower.split()

                    scored_docs = []
                    for doc in docs:
                        path_lower = doc.path.lower()
                        filename = os.path.basename(path_lower)

                        # Score based on query term matches in path/filename
                        score = 0
                        for term in query_terms:
                            if term in filename:
                                score += 10  # High weight for filename matches
                            elif term in path_lower:
                                score += 5  # Medium weight for path matches

                        if score > 0:
                            scored_docs.append((score, doc))

                    # Sort by score and take top k
                    scored_docs.sort(reverse=True, key=lambda x: x[0])
                    top_docs = scored_docs[:k]

                    if not top_docs:
                        return f"No documents found matching '{query}'. Try different search terms."

                    # Format response
                    result_parts = [
                        f"Found {len(top_docs)} relevant document(s) for '{query}':\n"
                    ]
                    for i, (score, doc) in enumerate(top_docs, 1):
                        filename = os.path.basename(doc.path)
                        indexed_status = (
                            "indexed" if doc.indexed else "not indexed"
                        )
                        result_parts.append(
                            f"{i}. {filename} ({indexed_status})"
                        )
                        result_parts.append(f"   Path: {doc.path}")

                    result_parts.append(
                        "\nTip: Use these document paths with rag_search to get detailed content."
                    )

                    return "\n".join(result_parts)
            except Exception as e:
                self.logger.error(f"Error searching knowledge base: {e}")
                return f"Error searching knowledge base: {str(e)}"

        return search_knowledge_base_documents

    def save_to_knowledge_base_tool(self) -> Callable:
        """Save text content to the knowledge base for RAG."""

        @tool
        def save_to_knowledge_base(
            content: str, title: str, category: str = "general"
        ) -> str:
            """Save content to the knowledge base for future RAG retrieval.

            This tool allows the agent to build its own knowledge base over time
            by saving important information for later reference.

            Args:
                content: Text content to save
                title: Title/identifier for this knowledge
                category: Category for organization (e.g., 'research', 'documentation')

            Returns:
                Confirmation message
            """
            try:
                # Create a document file
                base_path = os.path.expanduser("~/.local/share/airunner")
                kb_path = os.path.join(base_path, "knowledge_base", category)
                os.makedirs(kb_path, exist_ok=True)

                # Sanitize filename
                filename = "".join(
                    c for c in title if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                filename = filename.replace(" ", "_") + ".txt"

                file_path = os.path.join(kb_path, filename)

                # Write content
                with open(file_path, "w") as f:
                    f.write(f"Title: {title}\n")
                    f.write(f"Category: {category}\n")
                    f.write("\n---\n\n")
                    f.write(content)

                # Emit signal to reload RAG
                self.emit_signal(
                    SignalCode.RAG_DOCUMENT_ADDED,
                    {"file_path": file_path, "title": title},
                )

                return f"Content saved to knowledge base: {title}"
            except Exception as e:
                return f"Error saving to knowledge base: {str(e)}"

        return save_to_knowledge_base
