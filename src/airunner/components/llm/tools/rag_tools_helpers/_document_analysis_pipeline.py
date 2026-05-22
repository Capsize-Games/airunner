"""Deterministic map/reduce helpers for whole-document analysis."""

import re

from airunner.components.llm.tools.rag_tools_helpers._document_splitting import (
    select_evenly_spaced_items,
    split_document_paragraphs,
    split_document_sections,
    truncate_summary_evidence,
)

ANALYSIS_CHUNK_LIMIT = 6
CHUNK_PARAGRAPH_GROUP_SIZE = 2
QUERY_STOPWORDS = {
    "about",
    "across",
    "after",
    "analysis",
    "analyze",
    "describe",
    "document",
    "explain",
    "loaded",
    "please",
    "summarize",
    "summary",
    "themes",
    "transform",
    "using",
    "what",
    "which",
}


def extract_query_terms(query: str) -> set[str]:
    """Return one set of meaningful terms from the analysis request."""
    tokens = re.findall(r"[a-z0-9']+", str(query or "").lower())
    return {
        token
        for token in tokens
        if len(token) >= 4 and token not in QUERY_STOPWORDS
    }


def score_text_span(
    text: str,
    query_terms: set[str],
    *,
    position: int,
) -> int:
    """Score one paragraph span for chunk-level analysis."""
    normalized = str(text or "").lower()
    term_hits = sum(1 for term in query_terms if term in normalized)
    word_count = len(normalized.split())
    length_bonus = 1 if 8 <= word_count <= 80 else 0
    early_bonus = max(0, 3 - position)
    return term_hits * 4 + length_bonus + early_bonus


def select_chunk_summary_spans(
    spans: list[str],
    query_terms: set[str],
) -> list[str]:
    """Return the best paragraph spans for one chunk summary."""
    if len(spans) <= 2:
        return spans

    ranked = sorted(
        enumerate(spans),
        key=lambda item: (
            score_text_span(item[1], query_terms, position=item[0]),
            -item[0],
        ),
        reverse=True,
    )
    selected_indexes = sorted(index for index, _ in ranked[:2])
    return [spans[index] for index in selected_indexes]


def summarize_chunk_body(body: str, query_terms: set[str]) -> str:
    """Return one short summary for a chunk body."""
    spans = split_document_paragraphs(body, min_words=8)
    if not spans:
        cleaned = " ".join(str(body or "").split())
        return truncate_summary_evidence(cleaned, limit=320)

    selected = select_chunk_summary_spans(spans, query_terms)
    return truncate_summary_evidence(" ".join(selected), limit=320)


def group_paragraph_chunks(paragraphs: list[str]) -> list[tuple[str, str]]:
    """Group plain paragraphs into chunk-sized document regions."""
    chunks = []
    for start in range(0, len(paragraphs), CHUNK_PARAGRAPH_GROUP_SIZE):
        position = start // CHUNK_PARAGRAPH_GROUP_SIZE + 1
        body = "\n\n".join(
            paragraphs[start : start + CHUNK_PARAGRAPH_GROUP_SIZE]
        )
        chunks.append((f"Document region {position}", body))
    return chunks


def select_document_analysis_chunks(text: str) -> list[tuple[str, str]]:
    """Return representative chunk bodies for large-document analysis."""
    chunks = split_document_sections(text)
    if not chunks:
        paragraphs = split_document_paragraphs(text, min_words=8)
        if not paragraphs:
            return []
        chunks = group_paragraph_chunks(paragraphs)
    return select_evenly_spaced_items(chunks, ANALYSIS_CHUNK_LIMIT)


def build_chunk_analyses(query: str, text: str) -> list[dict[str, str]]:
    """Build map-stage summaries for representative document chunks."""
    analyses = []
    query_terms = extract_query_terms(query)
    for index, (title, body) in enumerate(
        select_document_analysis_chunks(text),
        1,
    ):
        summary = summarize_chunk_body(body, query_terms)
        if not summary:
            continue
        analyses.append(
            {
                "title": title or f"Document region {index}",
                "summary": summary,
            }
        )
    return analyses


def collect_unique_summaries(
    analyses: list[dict[str, str]],
    *,
    limit: int,
) -> list[str]:
    """Return unique chunk summaries while preserving order."""
    unique_summaries = []
    seen = set()
    for analysis in analyses:
        summary = str(analysis.get("summary", "") or "").strip()
        if not summary or summary in seen:
            continue
        seen.add(summary)
        unique_summaries.append(summary)
        if len(unique_summaries) >= limit:
            break
    return unique_summaries


def build_refined_document_synthesis(
    analyses: list[dict[str, str]],
) -> str:
    """Reduce chunk analyses into one whole-document synthesis."""
    if not analyses:
        return ""

    section_titles = [
        str(analysis.get("title", "") or "").strip()
        for analysis in analyses
        if str(analysis.get("title", "") or "").strip()
    ]
    lines = [f"Overview: {analyses[0]['summary']}"]
    if section_titles:
        lines.append("Covered sections: " + ", ".join(section_titles))

    key_developments = collect_unique_summaries(analyses[1:], limit=3)
    if key_developments:
        lines.append("Key developments:")
        lines.extend(
            f"{index}. {summary}"
            for index, summary in enumerate(key_developments, 1)
        )
    return "\n".join(lines)


def format_chunk_analyses(analyses: list[dict[str, str]]) -> str:
    """Format map-stage chunk summaries for tool output."""
    sections = []
    for index, analysis in enumerate(analyses, 1):
        title = str(analysis.get("title", "") or "").strip()
        summary = str(analysis.get("summary", "") or "").strip()
        sections.append(f"[Chunk {index} - {title}]\n{summary}")
    return "\n\n".join(sections)


__all__ = [
    "build_chunk_analyses",
    "build_refined_document_synthesis",
    "format_chunk_analyses",
]