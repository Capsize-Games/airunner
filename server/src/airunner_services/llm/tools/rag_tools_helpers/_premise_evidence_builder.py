"""Premise evidence selection helpers for document summary support."""

import re
from types import SimpleNamespace
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._document_splitting import (
    split_document_paragraphs,
    truncate_summary_evidence,
)
from airunner_services.llm.tools.rag_tools_helpers._premise_constants import (
    PREMISE_ROLE_LIMITS,
)
from airunner_services.llm.tools.rag_tools_helpers._premise_score_rules import (
    premise_current_setting_score,
    premise_dialogue_penalty,
    premise_inciting_incident_score,
    premise_neighbor_scene_score,
    premise_opening_score,
    premise_paragraph_score,
    premise_summary_label,
)
from airunner_services.llm.tools.rag_tools_helpers._shared import (
    SUMMARY_EVIDENCE_LIMIT,
)


def split_premise_regions(text: str) -> list[str]:
    """Return bounded sentence-like regions for long mixed paragraphs."""
    regions: list[str] = []
    seen: set[str] = set()
    for paragraph in split_document_paragraphs(text, min_words=1):
        for region in re.split(r"(?<=[.;?!])\s+", paragraph):
            cleaned = " ".join(region.split()).strip(" ;")
            if len(cleaned.split()) < 8 or cleaned in seen:
                continue
            seen.add(cleaned)
            regions.append(cleaned)
    return regions


def best_neighboring_scene_paragraph(
    paragraphs: list[str],
    center_index: int,
) -> str:
    """Return the best nearby current-scene paragraph for one hook."""
    candidates: list[tuple[int, int, str]] = []
    for neighbor_index in (center_index - 1, center_index + 1):
        if 0 <= neighbor_index < len(paragraphs):
            paragraph = paragraphs[neighbor_index]
            score = premise_neighbor_scene_score(paragraph)
            if score > 0:
                distance = abs(neighbor_index - center_index)
                candidates.append((score, distance, paragraph))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][2]


def best_early_current_setting_paragraph(paragraphs: list[str]) -> str:
    """Return the strongest early present-frame setting paragraph."""
    ranked = _ranked_early_setting_candidates(paragraphs)
    if not ranked:
        return ""
    early_candidates = [paragraph for score, _, paragraph in ranked if score >= 4]
    if early_candidates:
        return early_candidates[0]
    return ranked[0][2]


def build_premise_evidence_documents(
    metadata: dict[str, Any],
    text: str,
) -> list[Any]:
    """Build premise-focused evidence for book and document-about queries."""
    raw_paragraphs = split_document_paragraphs(text, min_words=1)
    paragraphs = split_document_paragraphs(text)
    if not paragraphs:
        return []
    state = _selection_state(min(SUMMARY_EVIDENCE_LIMIT, 6))
    _add_opening_setting(paragraphs, state)
    _add_opening_candidates(raw_paragraphs, paragraphs, state)
    _add_hook_candidates(paragraphs, state)
    _add_region_candidates(text, state)
    _add_early_window_candidates(paragraphs, state)
    return _selected_documents(metadata, state)


def _selection_state(limit: int) -> dict[str, Any]:
    """Return mutable selection state for premise evidence assembly."""
    return {
        "limit": limit,
        "selected": [],
        "seen": set(),
        "label_counts": {},
    }


def _add_selected(state: dict[str, Any], label: str, paragraph: str) -> None:
    """Append one labelled paragraph when it passes selection checks."""
    cleaned = str(paragraph or "").strip()
    if not cleaned or cleaned in state["seen"]:
        return
    label_limit = PREMISE_ROLE_LIMITS.get(label)
    label_counts = state["label_counts"]
    if label_limit is not None and label_counts.get(label, 0) >= label_limit:
        return
    state["seen"].add(cleaned)
    state["selected"].append((label, cleaned))
    label_counts[label] = label_counts.get(label, 0) + 1


def _add_opening_setting(paragraphs: list[str], state: dict[str, Any]) -> None:
    """Add the strongest early current-setting paragraph when available."""
    opening_setting = best_early_current_setting_paragraph(paragraphs)
    if opening_setting:
        _add_selected(state, "Current setting", opening_setting)


def _add_opening_candidates(
    raw_paragraphs: list[str],
    paragraphs: list[str],
    state: dict[str, Any],
) -> None:
    """Add strong opening-window candidates to the premise selection."""
    opening_window = _opening_window(raw_paragraphs, paragraphs)
    opening_limit = 2 if len(opening_window) > 3 else 1
    added_openings = 0
    for score, _, paragraph in _ranked_openings(opening_window):
        if score < 2:
            continue
        _add_selected(state, premise_summary_label(paragraph), paragraph)
        added_openings += 1
        if added_openings >= opening_limit:
            return


def _opening_window(
    raw_paragraphs: list[str],
    paragraphs: list[str],
) -> list[str]:
    """Return the opening window used for premise candidate scoring."""
    opening_window = [
        paragraph
        for paragraph in raw_paragraphs[:3]
        if len(paragraph.split()) >= 8
    ]
    if opening_window:
        return opening_window
    return paragraphs[: min(len(paragraphs), 3)]


def _ranked_openings(opening_window: list[str]) -> list[tuple[int, int, str]]:
    """Return ranked opening candidates by opening score then position."""
    return sorted(
        (
            (premise_opening_score(paragraph), index, paragraph)
            for index, paragraph in enumerate(opening_window)
        ),
        key=lambda item: (-item[0], item[1]),
    )


def _add_hook_candidates(paragraphs: list[str], state: dict[str, Any]) -> None:
    """Add scored hook paragraphs and optional current-scene neighbors."""
    hook_window = paragraphs[: min(len(paragraphs), 160)]
    for _, index, paragraph in _ranked_hooks(hook_window):
        _maybe_add_neighbor(hook_window, index, state)
        _add_selected(state, premise_summary_label(paragraph), paragraph)
        if len(state["selected"]) >= state["limit"]:
            return


def _ranked_hooks(paragraphs: list[str]) -> list[tuple[int, int, str]]:
    """Return ranked hook candidates by premise paragraph score."""
    scored_hooks = [
        (premise_paragraph_score(paragraph), index, paragraph)
        for index, paragraph in enumerate(paragraphs)
        if premise_paragraph_score(paragraph) > 0
    ]
    scored_hooks.sort(key=lambda item: (-item[0], item[1]))
    return scored_hooks


def _maybe_add_neighbor(
    hook_window: list[str],
    index: int,
    state: dict[str, Any],
) -> None:
    """Add one nearby current-scene paragraph when none is selected yet."""
    if len(state["selected"]) >= state["limit"] - 1:
        return
    if state["label_counts"].get("Current setting", 0) != 0:
        return
    neighbor = best_neighboring_scene_paragraph(hook_window, index)
    if neighbor:
        _add_selected(state, "Current setting", neighbor)


def _add_region_candidates(text: str, state: dict[str, Any]) -> None:
    """Add region-based fallback candidates when few spans were selected."""
    if len(state["selected"]) >= 3:
        return
    regions = split_premise_regions(text)
    for label, scorer in _role_scorers():
        for _, _, region in _ranked_regions(regions, scorer):
            _add_selected(state, label, region)
            break
        if len(state["selected"]) >= state["limit"]:
            return


def _role_scorers() -> tuple[tuple[str, Any], ...]:
    """Return the role scorers used for region-based premise fallbacks."""
    return (
        ("Current setting", premise_current_setting_score),
        ("Inciting incident", premise_inciting_incident_score),
    )


def _ranked_regions(
    regions: list[str],
    scorer: Any,
) -> list[tuple[int, int, str]]:
    """Return ranked region candidates for one premise role scorer."""
    return sorted(
        (
            (scorer(region), index, region)
            for index, region in enumerate(regions)
            if scorer(region) > 0
        ),
        key=lambda item: (-item[0], item[1]),
    )


def _add_early_window_candidates(
    paragraphs: list[str],
    state: dict[str, Any],
) -> None:
    """Add a final early-window fallback when evidence is still sparse."""
    if len(state["selected"]) >= 3:
        return
    for score, _, paragraph in _ranked_early_window(paragraphs):
        if score <= 0:
            continue
        _add_selected(state, premise_summary_label(paragraph), paragraph)
        if len(state["selected"]) >= state["limit"]:
            return


def _ranked_early_window(paragraphs: list[str]) -> list[tuple[int, int, str]]:
    """Return ranked fallback paragraphs from the early document window."""
    window_size = min(len(paragraphs), max(3, min(12, len(paragraphs) // 3)))
    early_window = paragraphs[:window_size]
    return sorted(
        (
            (_combined_early_score(paragraph), index, paragraph)
            for index, paragraph in enumerate(early_window)
        ),
        key=lambda item: (-item[0], item[1]),
    )


def _combined_early_score(paragraph: str) -> int:
    """Return the combined fallback score for one early paragraph."""
    return max(
        premise_paragraph_score(paragraph),
        premise_opening_score(paragraph) - premise_dialogue_penalty(paragraph),
    )


def _ranked_early_setting_candidates(
    paragraphs: list[str],
) -> list[tuple[int, int, str]]:
    """Return ranked early current-setting candidates by score then order."""
    if not paragraphs:
        return []
    window_limit = min(len(paragraphs), max(12, min(120, len(paragraphs) // 8)))
    ranked = [
        (premise_current_setting_score(paragraph), index, paragraph)
        for index, paragraph in enumerate(paragraphs[:window_limit])
        if premise_current_setting_score(paragraph) > 0
    ]
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return ranked


def _selected_documents(
    metadata: dict[str, Any],
    state: dict[str, Any],
) -> list[Any]:
    """Return selected premise evidence as simple namespace documents."""
    limit = state["limit"]
    return [
        SimpleNamespace(
            metadata=dict(metadata),
            page_content=f"{label}. {truncate_summary_evidence(paragraph)}",
        )
        for label, paragraph in state["selected"][:limit]
    ]