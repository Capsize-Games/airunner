"""
Shared helpers for knowledge tools.

Contains deduplication and merge logic used by recall_knowledge
to combine results from multiple search backends.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def merge_search_results(
    rag_results: list[str],
    keyword_results: list[dict[str, str]],
    tfidf_results: list[dict[str, str]],
) -> list[str]:
    """Merge and deduplicate search results from multiple sources.

    Results are combined in order: RAG first, then keyword,
    then TF-IDF. Duplicates (by normalized line content) are skipped.

    Args:
        rag_results: Results from RAG/semantic search.
        keyword_results: Results from keyword search
            (each a dict with a "line" key).
        tfidf_results: Results from TF-IDF search
            (each a dict with a "line" key).

    Returns:
        Deduplicated list of result strings.

    """
    seen: set[str] = set()
    results: list[str] = []

    def _add(line: str) -> None:
        clean = line.strip().lstrip("- ")
        if clean not in seen:
            results.append(clean)
            seen.add(clean)

    for r in rag_results:
        _add(r)
    for r in keyword_results:
        _add(r["line"])
    for r in tfidf_results:
        _add(r["line"])

    return results
