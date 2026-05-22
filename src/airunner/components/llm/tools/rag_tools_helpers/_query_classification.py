"""Query classification helpers for RAG tools."""

import re

from airunner.components.llm.utils.document_query_routing import (
    route_document_query,
)

_PREMISE_QUERY_PATTERNS = (
    r"\bwhat(?:'s| is)\s+(?:this|the)\s+"
    r"(?:book|novel|story|document|file)\s+about\b",
    r"\bwhat\s+is\s+the\s+(?:book|novel|story|document|file)\s+about\b",
    r"\btell\s+me\s+about\s+(?:this|the)\s+"
    r"(?:book|novel|story|document|file)\b",
)

_DOCUMENT_REFERENCE_PATTERNS = (
    r"\bit\b",
    r"\bits\b",
    r"\bthis document\b",
    r"\bthat document\b",
    r"\bthe document\b",
    r"\bthis file\b",
    r"\bthat file\b",
    r"\bthe file\b",
)


def _normalize_query(query: str) -> str:
    """Return one whitespace-normalized lowercase query string."""
    return " ".join(str(query or "").lower().split())


def query_mentions_document_reference(query: str) -> bool:
    """Return whether one query refers to one implied document."""
    normalized = _normalize_query(query)
    if not normalized:
        return False
    return any(
        re.search(pattern, normalized)
        for pattern in _DOCUMENT_REFERENCE_PATTERNS
    )


def is_summary_query(query: str) -> bool:
    """Return whether the query is asking for a document summary."""
    route = route_document_query(query, assume_document_mode=True)
    return route is not None and route.intent == "summary"


def is_premise_summary_query(query: str) -> bool:
    """Return whether the summary query is asking what a work is about."""
    normalized = _normalize_query(query)
    if not normalized:
        return False
    return any(
        re.search(pattern, normalized)
        for pattern in _PREMISE_QUERY_PATTERNS
    )


__all__ = [
    "is_premise_summary_query",
    "is_summary_query",
    "query_mentions_document_reference",
]