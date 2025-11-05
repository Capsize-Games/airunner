"""Agent-related utilities for LLM operations.

This module provides supporting components for the LLM system:
- RAGMixin: Retrieval-Augmented Generation using llama-index
- HtmlFileReader: HTML document reader
- WeatherMixin: Weather information integration
- CustomEpubReader: EPUB document reader
"""

__all__ = [
    "HtmlFileReader",
    "RAGMixin",
    "WeatherMixin",
    "CustomEpubReader",
]


def __getattr__(name):
    if name == "HtmlFileReader":
        from .html_file_reader import HtmlFileReader

        return HtmlFileReader
    elif name == "RAGMixin":
        from .rag_mixin import RAGMixin

        return RAGMixin
    elif name == "WeatherMixin":
        from .weather_mixin import WeatherMixin

        return WeatherMixin
    elif name == "CustomEpubReader":
        from .custom_epub_reader import CustomEpubReader

        return CustomEpubReader
    raise AttributeError(f"module {__name__} has no attribute {name}")
