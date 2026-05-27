"""Structured document-analysis helpers for document tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._document_splitting import (
    build_section_summary_units,
    select_evenly_spaced_items,
    split_document_paragraphs,
    split_document_sections,
    truncate_summary_evidence,
)
from airunner_services.llm.tools.rag_tools_helpers._structured_document_rendering import (
    build_structured_document_analysis_prompt as render_analysis_prompt,
    build_structured_premise_evidence_prompt as render_premise_prompt,
    format_structured_document_analysis as render_analysis_payload,
    format_structured_premise_evidence_documents as render_premise_docs,
)


PREMISE_CANDIDATE_LIMIT = 8


def request_structured_document_analysis_builder(
    rag_manager: Any,
) -> Callable[..., Any] | None:
    """Return one structured-analysis builder from the active manager."""
    builder = getattr(rag_manager, "build_structured_document_analysis", None)
    if callable(builder):
        return builder
    return None


def format_structured_document_analysis(payload: Any) -> str:
    """Return one stable string form for structured analysis payloads."""
    return render_analysis_payload(payload)


def build_structured_document_analysis_prompt(
    *,
    query: str,
    analyses: list[dict[str, str]],
    coverage_chunks: list[tuple[str, str]],
    refined_synthesis: str,
    evidence: list[Any],
    summary_focus: str | None,
) -> str:
    """Return one prompt for model-driven document-structure analysis."""
    return render_analysis_prompt(
        query=query,
        analyses=analyses,
        coverage_chunks=coverage_chunks,
        refined_synthesis=refined_synthesis,
        evidence=evidence,
        summary_focus=summary_focus,
    )


def build_structured_document_analysis(
    builder: Callable[..., Any] | None,
    *,
    metadata: dict[str, Any],
    query: str,
    analyses: list[dict[str, str]],
    evidence: list[Any],
    coverage_chunks: list[tuple[str, str]],
    refined_synthesis: str,
    summary_focus: str | None,
    logger: Any = None,
) -> str:
    """Return one formatted structured document-analysis block."""
    if not callable(builder):
        return ""
    try:
        payload = builder(
            metadata=metadata,
            query=query,
            analyses=analyses,
            evidence=evidence,
            coverage_chunks=coverage_chunks,
            refined_synthesis=refined_synthesis,
            summary_focus=summary_focus,
        )
    except Exception as error:
        if logger is not None:
            logger.warning(
                "Structured document analysis builder failed: %s",
                error,
            )
        return ""
    return format_structured_document_analysis(payload)


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
    return render_premise_prompt(
        query=query,
        candidates=candidates,
    )


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