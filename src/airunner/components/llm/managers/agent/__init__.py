"""Agent-related utilities for LLM operations."""

__all__ = [
    "DocumentBatchLoader",
    "DocumentVectorIndex",
    "RAGMixin",
    "WeatherMixin",
]


def __getattr__(name):
    if name == "DocumentBatchLoader":
        from .document_loader import DocumentBatchLoader

        return DocumentBatchLoader
    if name == "DocumentVectorIndex":
        from .vector_index import DocumentVectorIndex

        return DocumentVectorIndex
    if name == "RAGMixin":
        from .rag_mixin import RAGMixin

        return RAGMixin
    if name == "WeatherMixin":
        from .weather_mixin import WeatherMixin

        return WeatherMixin
    raise AttributeError(f"module {__name__} has no attribute {name}")
