"""Scoring rules for premise-oriented document summary evidence."""

import re

from airunner_services.llm.tools.rag_tools_helpers._premise_constants import (
    PREMISE_ATMOSPHERE_MARKERS,
    PREMISE_BACKSTORY_MARKERS,
    PREMISE_CONTEXT_MARKERS,
    PREMISE_DIALOGUE_MARKERS,
    PREMISE_DIALOGUE_SCENE_MARKERS,
    PREMISE_GROUNDED_MYSTERY_MARKERS,
    PREMISE_PLOT_MARKERS,
    PREMISE_PREFIX_MARKERS,
    PREMISE_SCENE_MARKERS,
)


def premise_has_marker(text: str, marker: str) -> bool:
    """Return whether one premise marker appears as an actual cue."""
    normalized_text = str(text or "").lower()
    normalized_marker = str(marker or "").lower().strip()
    if not normalized_text or not normalized_marker:
        return False
    if normalized_marker in PREMISE_PREFIX_MARKERS:
        pattern = rf"\b{re.escape(normalized_marker)}[a-z]*\b"
        return bool(re.search(pattern, normalized_text))
    if " " in normalized_marker:
        return normalized_marker in normalized_text
    pattern = rf"\b{re.escape(normalized_marker)}\b"
    return bool(re.search(pattern, normalized_text))


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
    lowered = str(paragraph or "").lower()
    if not lowered:
        return 0
    counts = _premise_hit_counts(lowered)
    if counts["plot"] == 0 or _is_backstory_only(counts):
        return 0
    mixed_scene = _has_mixed_current_scene(counts)
    score = _premise_score_value(counts, len(lowered.split()))
    penalty = _premise_penalty(paragraph, counts, mixed_scene)
    return max(0, score - penalty)


def premise_opening_score(paragraph: str) -> int:
    """Score one early paragraph for premise-level opening usefulness."""
    counts = _opening_counts(paragraph)
    if counts is None:
        return 0
    return max(
        0,
        counts["context"] * 3
        + counts["grounded"] * 2
        + counts["atmosphere"]
        + counts["scene"] * 4
        - counts["backstory"] * 4
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
    counts = _current_setting_counts(paragraph)
    if counts is None:
        return 0
    score = (
        counts["scene"] * 5
        + counts["context"] * 3
        + counts["grounded"] * 2
    )
    penalty = counts["backstory"] * 4
    penalty += min(premise_dialogue_penalty(paragraph), 4)
    return max(0, score - penalty)


def premise_inciting_incident_score(paragraph: str) -> int:
    """Score one span for the inciting case or catalyst."""
    counts = _incident_counts(paragraph)
    if counts is None:
        return 0
    score = counts["plot"] * 5 + counts["grounded"] * 4
    score += counts["scene"] * 2
    penalty = counts["backstory"] * 3
    penalty += min(premise_dialogue_penalty(paragraph), 4)
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


def _premise_hit_counts(lowered: str) -> dict[str, int]:
    """Return the marker hit counts used by the main paragraph score."""
    return {
        "plot": premise_count_hits(lowered, PREMISE_PLOT_MARKERS),
        "atmosphere": premise_count_hits(
            lowered,
            PREMISE_ATMOSPHERE_MARKERS,
        ),
        "context": premise_count_hits(lowered, PREMISE_CONTEXT_MARKERS),
        "grounded": premise_count_hits(
            lowered,
            PREMISE_GROUNDED_MYSTERY_MARKERS,
        ),
        "scene": premise_count_hits(lowered, PREMISE_SCENE_MARKERS),
        "backstory": premise_count_hits(
            lowered,
            PREMISE_BACKSTORY_MARKERS,
        ),
    }


def _is_backstory_only(counts: dict[str, int]) -> bool:
    """Return whether a paragraph reads like unsupported backstory only."""
    return (
        counts["backstory"]
        and not counts["scene"]
        and counts["plot"] <= 1
        and counts["grounded"] <= 2
    )


def _has_mixed_current_scene(counts: dict[str, int]) -> bool:
    """Return whether a paragraph mixes current-scene and hook cues."""
    return bool(
        counts["scene"]
        and (counts["plot"] or counts["grounded"] >= 2)
    )


def _premise_score_value(counts: dict[str, int], word_count: int) -> int:
    """Return the positive contribution for one paragraph score."""
    length_bonus = 1 if 20 <= word_count <= 140 else 0
    return (
        counts["plot"] * 5
        + counts["grounded"] * 3
        + counts["atmosphere"]
        + counts["context"]
        + counts["scene"] * 3
        + length_bonus
    )


def _premise_penalty(
    paragraph: str,
    counts: dict[str, int],
    mixed_scene: bool,
) -> int:
    """Return the penalty contribution for one paragraph score."""
    dialogue_penalty = premise_dialogue_penalty(paragraph)
    if mixed_scene:
        dialogue_penalty = min(dialogue_penalty, 2)
    penalty = dialogue_penalty + counts["backstory"] * 4
    if counts["scene"]:
        penalty = max(0, penalty - counts["scene"] * 3)
    if mixed_scene:
        penalty = max(0, penalty - counts["grounded"] * 2)
    return penalty


def _opening_counts(paragraph: str) -> dict[str, int] | None:
    """Return the marker hit counts used by the opening score."""
    lowered = str(paragraph or "").lower()
    if not lowered:
        return None
    return {
        "context": premise_count_hits(lowered, PREMISE_CONTEXT_MARKERS),
        "grounded": premise_count_hits(
            lowered,
            PREMISE_GROUNDED_MYSTERY_MARKERS,
        ),
        "atmosphere": premise_count_hits(
            lowered,
            PREMISE_ATMOSPHERE_MARKERS,
        ),
        "scene": premise_count_hits(lowered, PREMISE_SCENE_MARKERS),
        "backstory": premise_count_hits(
            lowered,
            PREMISE_BACKSTORY_MARKERS,
        ),
    }


def _current_setting_counts(paragraph: str) -> dict[str, int] | None:
    """Return the marker hit counts used by the current-setting score."""
    lowered = str(paragraph or "").lower()
    if not lowered:
        return None
    counts = {
        "scene": premise_count_hits(lowered, PREMISE_SCENE_MARKERS),
        "context": premise_count_hits(lowered, PREMISE_CONTEXT_MARKERS),
        "grounded": premise_count_hits(
            lowered,
            PREMISE_GROUNDED_MYSTERY_MARKERS,
        ),
        "backstory": premise_count_hits(
            lowered,
            PREMISE_BACKSTORY_MARKERS,
        ),
    }
    if counts["scene"] == 0 and counts["context"] == 0:
        return None
    return counts


def _incident_counts(paragraph: str) -> dict[str, int] | None:
    """Return the marker hit counts used by the incident score."""
    lowered = str(paragraph or "").lower()
    if not lowered:
        return None
    counts = {
        "plot": premise_count_hits(lowered, PREMISE_PLOT_MARKERS),
        "grounded": premise_count_hits(
            lowered,
            PREMISE_GROUNDED_MYSTERY_MARKERS,
        ),
        "scene": premise_count_hits(lowered, PREMISE_SCENE_MARKERS),
        "backstory": premise_count_hits(
            lowered,
            PREMISE_BACKSTORY_MARKERS,
        ),
    }
    if counts["plot"] == 0 and counts["grounded"] == 0:
        return None
    return counts