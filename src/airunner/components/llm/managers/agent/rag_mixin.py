"""RAG (Retrieval-Augmented Generation) system for document search.

This module provides a per-document RAG implementation with lazy loading
for scalability. Documents are indexed individually and only active documents
are loaded during search.

Architecture:
    - Per-document indexes stored in separate directories
    - Lazy loading of indexes (only load active documents)
    - Document registry tracks index metadata and status
    - LangChain integration for chat workflows
    - LlamaIndex for embedding and retrieval

The RAGMixin is composed of several focused mixins:
    - RAGPropertiesMixin: Configuration and property accessors
    - RAGDocumentMixin: Document database operations
    - RAGIndexManagementMixin: Index registry and CRUD
    - RAGIndexingMixin: Document indexing with progress reporting
    - RAGSearchMixin: Search and retrieval interface
    - RAGLifecycleMixin: Initialization and cleanup
"""
from airunner.components.llm.managers.agent.mixins import (
    RAGPropertiesMixin,
    RAGDocumentMixin,
    RAGIndexManagementMixin,
    RAGIndexingMixin,
    RAGSearchMixin,
    RAGLifecycleMixin,
)


class RAGMixin(
    RAGPropertiesMixin,
    RAGDocumentMixin,
    RAGIndexManagementMixin,
    RAGIndexingMixin,
    RAGSearchMixin,
    RAGLifecycleMixin,
):
    """Per-document RAG implementation with lazy loading for scalability.
    
    This class combines all RAG functionality through mixin inheritance.
    All methods and properties are provided by the mixins - see individual
    mixin docstrings for details.
    
    Usage:
        class MyClass(RAGMixin):
            def __init__(self):
                super().__init__()  # Initializes all RAG components
                
        # Search documents
        results = my_instance.search("query", k=5)
        
        # Index new documents
        my_instance.index_all_documents()
        
        # Reload after changes
        my_instance.reload_rag()
    """
