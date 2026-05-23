"""RAG (Retrieval-Augmented Generation) system for document search.

This module provides a per-document RAG implementation with lazy loading
for scalability. Documents are indexed individually and only active documents
are loaded during search.

Architecture:
    - Per-document indexes stored in separate directories
    - Lazy loading of indexes (only load active documents)
    - Document registry tracks index metadata and status
    - LangChain integration for chat workflows
    - LangChain-native embeddings, chunking, and retrieval

The RAGMixin is composed of several focused mixins:
    - RAGPropertiesMixin: Configuration and property accessors
    - RAGDocumentMixin: Document database operations
    - RAGIndexManagementMixin: Index registry and CRUD
    - RAGIndexingMixin: Document indexing with progress reporting
    - RAGSearchMixin: Search and retrieval interface
    - RAGLifecycleMixin: Initialization and cleanup
"""
from typing import Any

from airunner.components.llm.managers.agent.mixins import (
    RAGPropertiesMixin,
    RAGDocumentMixin,
    RAGIndexManagementMixin,
    RAGIndexingMixin,
    RAGSearchMixin,
    RAGLifecycleMixin,
)
from airunner.components.llm.tools.rag_tools_helpers._structured_document_analysis import (
    build_structured_document_analysis_prompt,
    build_structured_premise_candidate_spans,
    build_structured_premise_evidence_prompt,
    format_structured_premise_evidence_documents,
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

    def build_structured_document_analysis(
        self,
        *,
        metadata: dict[str, Any],
        query: str,
        analyses: list[dict[str, str]],
        evidence: list[Any],
        coverage_chunks: list[tuple[str, str]],
        refined_synthesis: str,
        summary_focus: str | None,
    ) -> dict[str, Any] | str:
        """Return model-built structured analysis for one document bundle."""
        invoke = getattr(self, "_invoke_request_preprocessor", None)
        extract_json = getattr(self, "_extract_json_object", None)
        if not callable(invoke) or not callable(extract_json):
            return ""

        prompt_text = build_structured_document_analysis_prompt(
            query=query,
            analyses=analyses,
            coverage_chunks=coverage_chunks,
            refined_synthesis=refined_synthesis,
            evidence=evidence,
            summary_focus=summary_focus,
        )
        response_text = invoke(prompt_text)
        if not response_text:
            return ""
        payload = extract_json(response_text)
        return payload if isinstance(payload, dict) else ""

    def build_structured_premise_evidence_documents(
        self,
        *,
        metadata: dict[str, Any],
        query: str,
        text: str,
    ) -> list[Any]:
        """Return model-selected premise evidence docs for one document."""
        invoke = getattr(self, "_invoke_request_preprocessor", None)
        extract_json = getattr(self, "_extract_json_object", None)
        if not callable(invoke) or not callable(extract_json):
            return []

        candidates = build_structured_premise_candidate_spans(text)
        if not candidates:
            return []
        prompt_text = build_structured_premise_evidence_prompt(
            query=query,
            candidates=candidates,
        )
        response_text = invoke(prompt_text)
        if not response_text:
            return []
        return format_structured_premise_evidence_documents(
            extract_json(response_text),
            candidates=candidates,
            metadata=metadata,
        )
