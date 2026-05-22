"""Premise-summary scoring helpers for RAG tools."""

import re
from types import SimpleNamespace
from typing import Any

from airunner.components.llm.tools.rag_tools_helpers._document_splitting import (
    split_document_paragraphs,
    truncate_summary_evidence,
)
from airunner.components.llm.tools.rag_tools_helpers._shared import (
    SUMMARY_EVIDENCE_LIMIT,
)

PREMISE_PLOT_MARKERS = (
    "body",
    "corpse",
    "detective",
    "investigat",
    "killed",
    "murder",
    "murderer",
    "mystery",
)

PREMISE_ATMOSPHERE_MARKERS = (
    "dead",
    "death",
)

PREMISE_CONTEXT_MARKERS = (
    "cemetery",
    "graveyard",
    "halloween",
    "hollywood",
    "studio",
)

PREMISE_GROUNDED_MYSTERY_MARKERS = (
    "accident",
    "apparently",
    "ally",
    "corruption",
    "disguise",
    "effects",
    "fake",
    "guest",
    "hoax",
    "hotel",
    "illusion",
    "illusions",
    "investigation",
    "investigat",
    "island",
    "killer",
    "makeup",
    "murder",
    "murderer",
    "mystery",
    "noir",
    "photograph",
    "photo",
    "snapshot",
    "return",
    "resort",
    "roller skates",
    "remember",
    "scheme",
    "schemes",
    "special effects",
    "supposedly",
    "trick",
    "wall",
)

PREMISE_SCENE_MARKERS = (
    "beach",
    "dining room",
    "guest",
    "guests",
    "hotel",
    "island",
    "pool",
    "resort",
    "room",
    "shore",
    "staying",
    "terrace",
    "verandah",
)

PREMISE_BACKSTORY_MARKERS = (
    "another country",
    "doctor's story",
    "had once",
    "old recollections",
    "once",
    "overseas",
    "recollection",
    "recollections",
    "reminiscence",
    "reminiscences",
    "story about",
    "told him",
    "told me",
    "told her",
    "used to",
    "years ago",
)

PREMISE_DIALOGUE_MARKERS = (
    " asked ",
    " cried ",
    " said ",
    " says ",
    " shouted ",
    " yelled ",
    " you ",
    " your ",
)

PREMISE_DIALOGUE_SCENE_MARKERS = (
    "career",
    "drink",
    "drunk",
    "lifestyle",
)

PREMISE_ROLE_LIMITS = {
    "Current setting": 1,
}

PREMISE_PREFIX_MARKERS = frozenset({"investigat"})


def premise_has_marker(text: str, marker: str) -> bool:
    """Return whether one premise marker appears as an actual cue."""
    normalized_text = str(text or "").lower()
    normalized_marker = str(marker or "").lower().strip()
    if not normalized_text or not normalized_marker:
        return False
    if normalized_marker in PREMISE_PREFIX_MARKERS:
        return bool(
            re.search(
                rf"\b{re.escape(normalized_marker)}[a-z]*\b",
                normalized_text,
            )
        )
    if " " in normalized_marker:
        return normalized_marker in normalized_text
    return bool(
        re.search(
            rf"\b{re.escape(normalized_marker)}\b",
            normalized_text,
        )
    )


def premise_count_hits(text: str, markers: tuple[str, ...]) -> int:
    """Return how many grounded markers appear in one text span."""
    lowered = str(text or "").lower()
    if not lowered:
        return 0
    return sum(premise_has_marker(lowered, marker) for marker in markers)


def premise_dialogue_penalty(paragraph: str) -> int:
    """Return one penalty for dialogue-heavy or accusatory side scenes."""
    source = str(paragraph or "")
    lowered = f" {source.lower()} "
    if not lowered.strip():
        return 0
    quote_hits = sum(source.count(char) for char in ('"', "“", "”"))
    dialogue_hits = sum(
        marker in lowered for marker in PREMISE_DIALOGUE_MARKERS
    )
    scene_hits = sum(
        marker in lowered for marker in PREMISE_DIALOGUE_SCENE_MARKERS
    )
    penalty = quote_hits * 2 + dialogue_hits * 3 + scene_hits * 2
    if quote_hits and (dialogue_hits or scene_hits):
        penalty += 6
    return penalty


def premise_paragraph_score(paragraph: str) -> int:
    """Score one paragraph for premise-level summary usefulness."""
    source = str(paragraph or "")
    lowered = source.lower()
    if not lowered:
        return 0

    plot_hits = premise_count_hits(lowered, PREMISE_PLOT_MARKERS)
    if plot_hits == 0:
        return 0
    atmosphere_hits = premise_count_hits(lowered, PREMISE_ATMOSPHERE_MARKERS)
    context_hits = premise_count_hits(lowered, PREMISE_CONTEXT_MARKERS)
    grounded_hits = premise_count_hits(
        lowered,
        PREMISE_GROUNDED_MYSTERY_MARKERS,
    )
    scene_hits = premise_count_hits(lowered, PREMISE_SCENE_MARKERS)
    backstory_hits = premise_count_hits(lowered, PREMISE_BACKSTORY_MARKERS)
    dialogue_penalty = premise_dialogue_penalty(source)
    mixed_current_scene = bool(scene_hits and (plot_hits or grounded_hits >= 2))
    word_count = len(lowered.split())
    length_bonus = 1 if 20 <= word_count <= 140 else 0
    if (
        backstory_hits
        and not scene_hits
        and plot_hits <= 1
        and grounded_hits <= 2
    ):
        return 0
    if mixed_current_scene:
        dialogue_penalty = min(dialogue_penalty, 2)
    score = (
        plot_hits * 5
        + grounded_hits * 3
        + atmosphere_hits
        + context_hits
        + scene_hits * 3
        + length_bonus
    )
    penalty = dialogue_penalty + backstory_hits * 4
    if scene_hits:
        penalty = max(0, penalty - scene_hits * 3)
    if mixed_current_scene:
        penalty = max(0, penalty - grounded_hits * 2)
    return max(0, score - penalty)


def premise_opening_score(paragraph: str) -> int:
    """Score one early paragraph for premise-level opening usefulness."""
    lowered = str(paragraph or "").lower()
    if not lowered:
        return 0
    context_hits = premise_count_hits(lowered, PREMISE_CONTEXT_MARKERS)
    grounded_hits = premise_count_hits(
        lowered,
        PREMISE_GROUNDED_MYSTERY_MARKERS,
    )
    atmosphere_hits = premise_count_hits(
        lowered,
        PREMISE_ATMOSPHERE_MARKERS,
    )
    scene_hits = premise_count_hits(lowered, PREMISE_SCENE_MARKERS)
    backstory_hits = premise_count_hits(lowered, PREMISE_BACKSTORY_MARKERS)
    return max(
        0,
        context_hits * 3
        + grounded_hits * 2
        + atmosphere_hits
        + scene_hits * 4
        - backstory_hits * 4
        - min(premise_dialogue_penalty(paragraph), 4),
    )


def premise_neighbor_scene_score(paragraph: str) -> int:
    """Score one neighboring paragraph for current-scene support."""
    lowered = str(paragraph or "").lower()
    if not lowered:
        return 0
    scene_hits = premise_count_hits(lowered, PREMISE_SCENE_MARKERS)
    if scene_hits == 0:
        return 0
    context_hits = premise_count_hits(lowered, PREMISE_CONTEXT_MARKERS)
    backstory_hits = premise_count_hits(lowered, PREMISE_BACKSTORY_MARKERS)
    score = scene_hits * 4 + context_hits * 2 - backstory_hits * 4
    return max(0, score - min(premise_dialogue_penalty(paragraph), 4))


def premise_current_setting_score(paragraph: str) -> int:
    """Score one span for present-frame setting value."""
    lowered = str(paragraph or "").lower()
    if not lowered:
        return 0
    scene_hits = premise_count_hits(lowered, PREMISE_SCENE_MARKERS)
    context_hits = premise_count_hits(lowered, PREMISE_CONTEXT_MARKERS)
    grounded_hits = premise_count_hits(
        lowered,
        PREMISE_GROUNDED_MYSTERY_MARKERS,
    )
    backstory_hits = premise_count_hits(lowered, PREMISE_BACKSTORY_MARKERS)
    if scene_hits == 0 and context_hits == 0:
        return 0
    score = scene_hits * 5 + context_hits * 3 + grounded_hits * 2
    penalty = backstory_hits * 4 + min(premise_dialogue_penalty(paragraph), 4)
    return max(0, score - penalty)


def premise_inciting_incident_score(paragraph: str) -> int:
    """Score one span for the inciting case or catalyst."""
    lowered = str(paragraph or "").lower()
    if not lowered:
        return 0
    plot_hits = premise_count_hits(lowered, PREMISE_PLOT_MARKERS)
    grounded_hits = premise_count_hits(
        lowered,
        PREMISE_GROUNDED_MYSTERY_MARKERS,
    )
    scene_hits = premise_count_hits(lowered, PREMISE_SCENE_MARKERS)
    backstory_hits = premise_count_hits(lowered, PREMISE_BACKSTORY_MARKERS)
    if plot_hits == 0 and grounded_hits == 0:
        return 0
    score = plot_hits * 5 + grounded_hits * 4 + scene_hits * 2
    penalty = backstory_hits * 3 + min(premise_dialogue_penalty(paragraph), 4)
    return max(0, score - penalty)


def premise_summary_label(paragraph: str) -> str:
    """Return the clearest evidence role label for one span."""
    current_score = premise_current_setting_score(paragraph)
    incident_score = premise_inciting_incident_score(paragraph)
    if incident_score >= current_score and incident_score >= 4:
        return "Inciting incident"
    if current_score >= 4:
        return "Current setting"
    return "Premise detail"


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
                candidates.append(
                    (score, abs(neighbor_index - center_index), paragraph)
                )
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][2]


def build_premise_evidence_documents(
    metadata: dict[str, Any],
    text: str,
) -> list[Any]:
    """Build premise-focused evidence for book and document-about queries."""
    raw_paragraphs = split_document_paragraphs(text, min_words=1)
    paragraphs = split_document_paragraphs(text)
    if not paragraphs:
        return []

    premise_limit = min(SUMMARY_EVIDENCE_LIMIT, 6)
    selected: list[tuple[str, str]] = []
    seen: set[str] = set()
    label_counts: dict[str, int] = {}

    def add(label: str, paragraph: str) -> None:
        cleaned = str(paragraph or "").strip()
        if not cleaned or cleaned in seen:
            return
        label_limit = PREMISE_ROLE_LIMITS.get(label)
        if label_limit is not None and label_counts.get(label, 0) >= label_limit:
            return
        seen.add(cleaned)
        selected.append((label, cleaned))
        label_counts[label] = label_counts.get(label, 0) + 1

    opening_window = [
        paragraph
        for paragraph in raw_paragraphs[:3]
        if len(paragraph.split()) >= 8
    ]
    if not opening_window:
        opening_window = paragraphs[: min(len(paragraphs), 3)]

    scored_openings = sorted(
        (
            (premise_opening_score(paragraph), index, paragraph)
            for index, paragraph in enumerate(opening_window)
        ),
        key=lambda item: (-item[0], item[1]),
    )
    opening_limit = 2 if len(opening_window) > 3 else 1
    added_openings = 0
    for score, _index, paragraph in scored_openings:
        if score < 2:
            continue
        add(premise_summary_label(paragraph), paragraph)
        added_openings += 1
        if added_openings >= opening_limit:
            break

    hook_window = paragraphs[: min(len(paragraphs), 160)]
    scored_hooks = [
        (premise_paragraph_score(paragraph), index, paragraph)
        for index, paragraph in enumerate(hook_window)
        if premise_paragraph_score(paragraph) > 0
    ]
    scored_hooks.sort(key=lambda item: (-item[0], item[1]))
    for _score, index, paragraph in scored_hooks:
        if len(selected) < premise_limit - 1:
            neighbor = best_neighboring_scene_paragraph(hook_window, index)
            if neighbor:
                add("Current setting", neighbor)
        add(premise_summary_label(paragraph), paragraph)
        if len(selected) >= premise_limit:
            break

    if len(selected) < 3:
        regions = split_premise_regions(text)
        role_scorers = (
            ("Current setting", premise_current_setting_score),
            ("Inciting incident", premise_inciting_incident_score),
        )
        for label, scorer in role_scorers:
            ranked_regions = sorted(
                (
                    (scorer(region), index, region)
                    for index, region in enumerate(regions)
                    if scorer(region) > 0
                ),
                key=lambda item: (-item[0], item[1]),
            )
            for _score, _index, region in ranked_regions:
                add(label, region)
                break
            if len(selected) >= premise_limit:
                break

    if len(selected) < 3:
        opening_window_size = min(
            len(paragraphs),
            max(3, min(12, len(paragraphs) // 3)),
        )
        early_window = paragraphs[:opening_window_size]
        scored_early_window = sorted(
            (
                (
                    max(
                        premise_paragraph_score(paragraph),
                        premise_opening_score(paragraph)
                        - premise_dialogue_penalty(paragraph),
                    ),
                    index,
                    paragraph,
                )
                for index, paragraph in enumerate(early_window)
            ),
            key=lambda item: (-item[0], item[1]),
        )
        for score, _index, paragraph in scored_early_window:
            if score <= 0:
                continue
            add(premise_summary_label(paragraph), paragraph)
            if len(selected) >= premise_limit:
                break

    return [
        SimpleNamespace(
            metadata=dict(metadata),
            page_content=f"{label}. {truncate_summary_evidence(paragraph)}",
        )
        for label, paragraph in selected[:premise_limit]
    ]


__all__ = [
    "build_premise_evidence_documents",
]