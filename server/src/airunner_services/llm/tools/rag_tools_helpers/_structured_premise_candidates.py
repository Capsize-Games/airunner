"""Structured premise-candidate helpers for document tools."""

from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._document_splitting import (
    build_section_summary_units,
    select_evenly_spaced_items,
    split_document_paragraphs,
    split_document_sections,
    truncate_summary_evidence,
)
from airunner_services.llm.tools.rag_tools_helpers._structured_document_rendering import (
    build_structured_premise_evidence_prompt as render_premise_prompt,
    format_structured_premise_evidence_documents as render_premise_docs,
)

PREMISE_CANDIDATE_LIMIT = 8


def _build_section_premise_candidates(
    text: str,
) -> list[dict[str, str | int]]:
    """Return early section-based premise candidates."""
    units = build_section_summary_units(split_document_sections(text))
    return [
        {
            "candidate_id": f"span_{index}",
            "position": index,
            "source": title or f"Document region {index}",
            "text": truncate_summary_evidence(body, limit=360),
        }
        for index, (title, body) in enumerate(
            units[:PREMISE_CANDIDATE_LIMIT],
            1,
        )
        if str(body or "").strip()
    ]


def _build_paragraph_premise_candidates(
    text: str,
) -> list[dict[str, str | int]]:
    """Return early paragraph-based premise candidates."""
    paragraphs = split_document_paragraphs(text, min_words=8)
    window = paragraphs[: max(PREMISE_CANDIDATE_LIMIT, 12)]
    selected = select_evenly_spaced_items(
        window,
        min(PREMISE_CANDIDATE_LIMIT, len(window)),
    )
    return [
        {
            "candidate_id": f"span_{index}",
            "position": index,
            "source": f"Document region {index}",
            "text": truncate_summary_evidence(paragraph, limit=360),
        }
        for index, paragraph in enumerate(selected, 1)
        if str(paragraph or "").strip()
    ]


def build_structured_premise_candidate_spans(
    text: str,
) -> list[dict[str, str | int]]:
    """Return representative premise candidates from document structure."""
    section_candidates = _build_section_premise_candidates(text)
    if section_candidates:
        return section_candidates
    return _build_paragraph_premise_candidates(text)


def build_structured_premise_evidence_prompt(
    *,
    query: str,
    candidates: list[dict[str, str | int]],
) -> str:
    """Return one prompt for model-driven premise evidence selection."""
    return render_premise_prompt(query=query, candidates=candidates)


def format_structured_premise_evidence_documents(
    payload: Any,
    *,
    candidates: list[dict[str, str | int]],
    metadata: dict[str, Any],
) -> list[Any]:
    """Return premise evidence docs selected by a structured payload."""
    return render_premise_docs(
        payload,
        candidates=candidates,
        metadata=metadata,
    )
