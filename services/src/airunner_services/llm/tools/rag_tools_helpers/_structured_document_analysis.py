"""Structured document-analysis helpers for document tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._structured_document_rendering import (
    build_structured_document_analysis_prompt as render_analysis_prompt,
    format_structured_document_analysis as render_analysis_payload,
)
from airunner_services.llm.tools.rag_tools_helpers._structured_premise_candidates import (
    build_structured_premise_candidate_spans,
    build_structured_premise_evidence_prompt,
    format_structured_premise_evidence_documents,
)


StructuredAnalyses = list[dict[str, str]]
CoverageChunks = list[tuple[str, str]]


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
    builder: Callable[..., Any] | None, *, metadata: dict[str, Any],
    query: str, analyses: StructuredAnalyses, evidence: list[Any],
    coverage_chunks: CoverageChunks, refined_synthesis: str,
    summary_focus: str | None,
    logger: Any = None,
) -> str:
    """Return one formatted structured document-analysis block."""
    if not callable(builder):
        return ""
    payload = _invoke_structured_document_analysis_builder(
        builder, metadata=metadata, query=query, analyses=analyses,
        evidence=evidence, coverage_chunks=coverage_chunks,
        refined_synthesis=refined_synthesis, summary_focus=summary_focus,
        logger=logger,
    )
    if payload is None:
        return ""
    return format_structured_document_analysis(payload)


def _invoke_structured_document_analysis_builder(
    builder: Callable[..., Any], *, metadata: dict[str, Any],
    query: str, analyses: StructuredAnalyses, evidence: list[Any],
    coverage_chunks: CoverageChunks, refined_synthesis: str,
    summary_focus: str | None,
    logger: Any,
) -> Any | None:
    """Invoke the structured-analysis builder and normalize failures."""
    try:
        return builder(
            metadata=metadata, query=query, analyses=analyses,
            evidence=evidence, coverage_chunks=coverage_chunks,
            refined_synthesis=refined_synthesis,
            summary_focus=summary_focus,
        )
    except Exception as error:
        if logger is not None:
            logger.warning(
                "Structured document analysis builder failed: %s",
                error,
            )
        return None