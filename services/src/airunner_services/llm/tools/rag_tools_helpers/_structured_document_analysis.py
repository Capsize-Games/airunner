"""Structured document-analysis helpers for document tools."""

from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from airunner.components.llm.tools.rag_tools_helpers._document_splitting import (
    build_section_summary_units,
    select_evenly_spaced_items,
    split_document_paragraphs,
    split_document_sections,
    truncate_summary_evidence,
)
from airunner.components.llm.tools.rag_tools_helpers._shared import (
    SUMMARY_EVIDENCE_LIMIT,
)


PREMISE_CANDIDATE_LIMIT = 8
PREMISE_EVIDENCE_ROLES = {
    "Background detail",
    "Current setting",
    "Frame narrative",
    "Inciting incident",
    "Premise detail",
    "Production context",
    "Relationship or stakes",
}


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
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, (dict, list)):
        try:
            return json.dumps(payload, indent=2, sort_keys=True)
        except Exception:
            return ""
    return ""


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
    coverage_lines = [
        f"- {title or f'Document region {index}'}"
        for index, (title, _body) in enumerate(coverage_chunks[:6], 1)
    ]
    chunk_lines = [
        f"- {analysis.get('title', 'Document region')}: "
        f"{analysis.get('summary', '')}"
        for analysis in analyses[:6]
    ]
    evidence_lines = [
        f"- {str(getattr(item, 'page_content', '') or '').strip()}"
        for item in evidence[:4]
        if str(getattr(item, 'page_content', '') or '').strip()
    ]
    return (
        "You are AIRunner's internal structured document analyst. "
        "Read the grounded document-analysis bundle and return ONLY JSON.\n\n"
        "Required JSON schema:\n"
        "{\n"
        '  "primary_narrative_layer": "story_world|frame_or_recollection|'
        'layered_or_mixed|non_fiction_or_argument|unclear",\n'
        '  "secondary_narrative_layers": ["production_process"],\n'
        '  "summary_priority": ["setting", "inciting_conflict"],\n'
        '  "composition_cautions": ["short grounded caution"]\n'
        "}\n"
        "Rules:\n"
        "- Use only the analysis bundle below.\n"
        "- Do not infer from title, author, or genre alone.\n"
        "- When the bundle mixes story-world events with production, "
        "staging, authorship, recollection, or quoted framing, record "
        "that extra layer in secondary_narrative_layers instead of "
        "flattening it into literal plot.\n"
        "- Use layered_or_mixed when more than one grounded narrative "
        "layer materially shapes how a safe summary should be composed.\n"
        "- Keep composition_cautions short and actionable.\n"
        "- Use [] when a list field has no supported items.\n"
        "- Do not include explanations outside the JSON object.\n\n"
        f"Requested analysis: {query}\n"
        f"Summary focus: {summary_focus or 'none'}\n\n"
        "Document coverage:\n"
        f"{chr(10).join(coverage_lines) or '- none'}\n\n"
        "Refined whole-document synthesis:\n"
        f"{refined_synthesis or 'none'}\n\n"
        "Chunk summaries:\n"
        f"{chr(10).join(chunk_lines) or '- none'}\n\n"
        "Supporting evidence:\n"
        f"{chr(10).join(evidence_lines) or '- none'}"
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
    candidate_lines = [
        f"- {candidate['candidate_id']} | source={candidate['source']} | "
        f"text={candidate['text']}"
        for candidate in candidates
    ]
    return (
        "You are AIRunner's internal premise-evidence selector. "
        "Read the candidate spans and return ONLY JSON.\n\n"
        "Required JSON schema:\n"
        "{\n"
        '  "selected_spans": [\n'
        '    {"candidate_id": "span_1", '
        '"role": "Current setting"}\n'
        "  ],\n"
        '  "composition_cautions": ["short grounded caution"]\n'
        "}\n"
        "Allowed role values:\n"
        "- Current setting\n"
        "- Inciting incident\n"
        "- Relationship or stakes\n"
        "- Premise detail\n"
        "- Production context\n"
        "- Frame narrative\n"
        "- Background detail\n"
        "Rules:\n"
        "- Use only listed candidate_id values.\n"
        "- Select up to 6 spans.\n"
        "- Order them by importance for answering what the document is "
        "about.\n"
        "- If staged, quoted, remembered, or frame-level material appears, "
        "label it as Production context, Frame narrative, or Background "
        "detail unless the span clearly states literal plot events.\n"
        "- Do not include explanations outside the JSON object.\n\n"
        f"User question: {query}\n\n"
        "Candidate spans:\n"
        f"{chr(10).join(candidate_lines) or '- none'}"
    )


def format_structured_premise_evidence_documents(
    payload: Any,
    *,
    candidates: list[dict[str, str | int]],
    metadata: dict[str, Any],
) -> list[Any]:
    """Return premise evidence docs selected by a structured payload."""
    if not isinstance(payload, dict):
        return []
    selected_spans = payload.get("selected_spans")
    if not isinstance(selected_spans, list):
        return []

    candidate_map = {
        str(candidate.get("candidate_id") or ""): candidate
        for candidate in candidates
    }
    selected_docs = []
    seen_ids: set[str] = set()
    for item in selected_spans[:SUMMARY_EVIDENCE_LIMIT]:
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("candidate_id") or "").strip()
        role = str(item.get("role") or "").strip()
        if (
            not candidate_id
            or candidate_id in seen_ids
            or role not in PREMISE_EVIDENCE_ROLES
        ):
            continue
        candidate = candidate_map.get(candidate_id)
        if candidate is None:
            continue
        seen_ids.add(candidate_id)
        selected_docs.append(
            SimpleNamespace(
                metadata=dict(metadata),
                page_content=f"{role}. {candidate['text']}",
            )
        )
    return selected_docs