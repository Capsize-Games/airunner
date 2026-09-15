"""Service-owned top-level RAG mixin composition."""

from airunner_services.llm.managers.agent.mixins import (
    RAGDocumentMixin,
    RAGIndexingMixin,
    RAGIndexManagementMixin,
    RAGLifecycleMixin,
    RAGPropertiesMixin,
    RAGSearchMixin,
)


class RAGMixin(
    RAGPropertiesMixin,
    RAGDocumentMixin,
    RAGIndexManagementMixin,
    RAGIndexingMixin,
    RAGSearchMixin,
    RAGLifecycleMixin,
):
    """Per-document RAG implementation with lazy loading."""


__all__ = ["RAGMixin"]