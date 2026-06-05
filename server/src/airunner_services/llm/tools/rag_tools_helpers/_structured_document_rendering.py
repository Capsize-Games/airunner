"""Prompt and output rendering helpers for structured document analysis."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._shared import (
    SUMMARY_EVIDENCE_LIMIT,
)

PREMISE_EVIDENCE_ROLE_ORDER = (
    "Current setting",
    "Inciting incident",
    "Relationship or stakes",
    "Premise detail",
    "Production context",
    "Frame narrative",
    "Background detail",
)

PREMISE_EVIDENCE_ROLES = set(PREMISE_EVIDENCE_ROLE_ORDER)

STRUCTURED_ANALYSIS_SCHEMA = (
    "Required JSON schema:\n"
    "{\n"
    '  "primary_narrative_layer": "story_world|frame_or_recollection|'
    'layered_or_mixed|non_fiction_or_argument|unclear",\n'
    '  "secondary_narrative_layers": ["production_process"],\n'
    '  "summary_priority": ["setting", "inciting_conflict"],\n'
    '  "composition_cautions": ["short grounded caution"]\n'
    "}"
)

STRUCTURED_ANALYSIS_RULES = (
    "Rules:\n"
    "- Use only the analysis bundle below.\n"
    "- Do not infer from title, author, or genre alone.\n"
    "- When the bundle mixes story-world events with production, staging, "
    "authorship, recollection, or quoted framing, record that extra layer in "
    "secondary_narrative_layers instead of flattening it into literal plot.\n"
    "- Use layered_or_mixed when more than one grounded narrative layer "
    "materially shapes how a safe summary should be composed.\n"
    "- Keep composition_cautions short and actionable.\n"
    "- Use [] when a list field has no supported items.\n"
    "- Do not include explanations outside the JSON object."
)

PREMISE_EVIDENCE_SCHEMA = (
    "Required JSON schema:\n"
    "{\n"
    '  "selected_spans": [\n'
    '    {"candidate_id": "span_1", "role": "Current setting"}\n'
    "  ],\n"
    '  "composition_cautions": ["short grounded caution"]\n'
    "}"
)

PREMISE_EVIDENCE_RULES = (
    "Rules:\n"
    "- Use only listed candidate_id values.\n"
    "- Select up to 6 spans.\n"
    "- Order them by importance for answering what the document is about.\n"
    "- If staged, quoted, remembered, or frame-level material appears, label "
    "it as Production context, Frame narrative, or Background detail unless "
    "the span clearly states literal plot events.\n"
    "- Do not include explanations outside the JSON object."
)


def format_structured_document_analysis(payload: Any) -> str:
    """Return a stable string form for structured analysis payloads."""
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
    """Return the structured document-analysis prompt."""
    sections = [
        "You are AIRunner's internal structured document analyst. Read the "
        "grounded document-analysis bundle and return ONLY JSON.",
        STRUCTURED_ANALYSIS_SCHEMA,
        STRUCTURED_ANALYSIS_RULES,
        f"Requested analysis: {query}\nSummary focus: {summary_focus or 'none'}",
        "Document coverage:\n"
        + _joined_lines(_coverage_lines(coverage_chunks)),
        "Refined whole-document synthesis:\n" + (refined_synthesis or "none"),
        "Chunk summaries:\n" + _joined_lines(_chunk_lines(analyses)),
        "Supporting evidence:\n" + _joined_lines(_evidence_lines(evidence)),
    ]
    return "\n\n".join(sections)


def build_structured_premise_evidence_prompt(
    *,
    query: str,
    candidates: list[dict[str, str | int]],
) -> str:
    """Return the structured premise-evidence selection prompt."""
    role_lines = "\n".join(f"- {role}" for role in PREMISE_EVIDENCE_ROLE_ORDER)
    sections = [
        "You are AIRunner's internal premise-evidence selector. Read the "
        "candidate spans and return ONLY JSON.",
        PREMISE_EVIDENCE_SCHEMA,
        f"Allowed role values:\n{role_lines}",
        PREMISE_EVIDENCE_RULES,
        f"User question: {query}",
        "Candidate spans:\n" + _joined_lines(_candidate_lines(candidates)),
    ]
    return "\n\n".join(sections)


def format_structured_premise_evidence_documents(
    payload: Any,
    *,
    candidates: list[dict[str, str | int]],
    metadata: dict[str, Any],
) -> list[Any]:
    """Return premise evidence docs selected by a structured payload."""
    selected_spans = _selected_spans(payload)
    if selected_spans is None:
        return []
    candidate_map = _candidate_map(candidates)
    seen_ids: set[str] = set()
    selected_docs: list[Any] = []
    for item in selected_spans[:SUMMARY_EVIDENCE_LIMIT]:
        doc = _selected_span_document(item, candidate_map, metadata, seen_ids)
        if doc is not None:
            selected_docs.append(doc)
    return selected_docs


def _coverage_lines(coverage_chunks: list[tuple[str, str]]) -> list[str]:
    """Return formatted coverage lines for the analysis prompt."""
    return [
        f"- {title or f'Document region {index}'}"
        for index, (title, _body) in enumerate(coverage_chunks[:6], 1)
    ]


def _chunk_lines(analyses: list[dict[str, str]]) -> list[str]:
    """Return formatted chunk summary lines for the analysis prompt."""
    return [
        f"- {analysis.get('title', 'Document region')}: "
        f"{analysis.get('summary', '')}"
        for analysis in analyses[:6]
    ]


def _evidence_lines(evidence: list[Any]) -> list[str]:
    """Return formatted supporting evidence lines for the analysis prompt."""
    return [
        f"- {text}"
        for item in evidence[:4]
        if (text := str(getattr(item, "page_content", "") or "").strip())
    ]


def _candidate_lines(candidates: list[dict[str, str | int]]) -> list[str]:
    """Return formatted candidate span lines for the premise prompt."""
    return [
        f"- {candidate['candidate_id']} | source={candidate['source']} | "
        f"text={candidate['text']}"
        for candidate in candidates
    ]


def _joined_lines(lines: list[str]) -> str:
    """Return fallback-safe joined lines for prompt sections."""
    return "\n".join(lines) or "- none"


def _selected_spans(payload: Any) -> list[dict[str, Any]] | None:
    """Return the selected span list when the payload is valid."""
    if not isinstance(payload, dict):
        return None
    selected_spans = payload.get("selected_spans")
    if isinstance(selected_spans, list):
        return selected_spans
    return None


def _candidate_map(
    candidates: list[dict[str, str | int]],
) -> dict[str, dict[str, str | int]]:
    """Return candidate entries keyed by candidate id."""
    return {
        str(candidate.get("candidate_id") or ""): candidate
        for candidate in candidates
    }


def _selected_span_document(
    item: Any,
    candidate_map: dict[str, dict[str, str | int]],
    metadata: dict[str, Any],
    seen_ids: set[str],
) -> Any | None:
    """Return one selected evidence document when a span item is valid."""
    candidate_id, role = _selected_span_identity(item)
    if (
        not candidate_id
        or candidate_id in seen_ids
        or role not in PREMISE_EVIDENCE_ROLES
    ):
        return None
    candidate = candidate_map.get(candidate_id)
    if candidate is None:
        return None
    seen_ids.add(candidate_id)
    return SimpleNamespace(
        metadata=dict(metadata),
        page_content=f"{role}. {candidate['text']}",
    )


def _selected_span_identity(item: Any) -> tuple[str, str]:
    """Return the candidate id and role for one selected span payload."""
    if not isinstance(item, dict):
        return "", ""
    candidate_id = str(item.get("candidate_id") or "").strip()
    role = str(item.get("role") or "").strip()
    return candidate_id, role
