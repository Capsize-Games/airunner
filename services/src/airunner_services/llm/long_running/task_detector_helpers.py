"""Signal-detection helpers for task-complexity analysis."""

from __future__ import annotations

import re
from typing import Optional

from airunner_services.llm.long_running.task_detector_patterns import (
    ANALYSIS_KEYWORDS,
    CODING_COMPOUND_PATTERNS,
    CODING_PROJECT_KEYWORDS,
    MULTI_ITEM_PATTERNS,
    RESEARCH_PATTERNS,
)
from airunner_services.llm.long_running.task_detector_state import (
    DetectionState,
    matched_count,
    matched_group_count,
    record_reason,
)


def apply_multi_item_patterns(
    prompt_lower: str,
    state: DetectionState,
) -> None:
    """Apply explicit multi-item pattern detection."""
    for pattern in MULTI_ITEM_PATTERNS:
        match = re.search(pattern, prompt_lower)
        if match:
            record_reason(state, 0.9,
                          f"Explicit multi-item pattern: {match.group(0)[:50]}")
            count = matched_count(match.group(0))
            if count is not None:
                state.detected_items = [f"item_{index + 1}" for index in range(count)]


def apply_research_patterns(prompt_lower: str, state: DetectionState) -> None:
    """Apply research-specific pattern detection."""
    for pattern in RESEARCH_PATTERNS:
        match = re.search(pattern, prompt_lower)
        if match:
            record_reason(state, 0.85,
                          f"Research pattern detected: {match.group(0)}")
            count = matched_group_count(match)
            if count is not None:
                state.detected_items = [
                    f"research_topic_{index + 1}" for index in range(count)
                ]


def apply_coding_patterns(prompt_lower: str, state: DetectionState) -> None:
    """Apply coding-project keyword and compound-pattern detection."""
    coding_score = coding_keyword_score(prompt_lower)
    coding_score += compound_coding_score(prompt_lower, state)
    if coding_score >= 2:
        record_reason(state, 0.7,
                      f"Multiple implementation keywords ({coding_score})")
    elif coding_score == 1:
        record_reason(state, 0.4, "Single implementation keyword")


def coding_keyword_score(prompt_lower: str) -> int:
    """Return the implementation-keyword score for one prompt."""
    return sum(1 for keyword in CODING_PROJECT_KEYWORDS if keyword in prompt_lower)


def compound_coding_score(prompt_lower: str, state: DetectionState) -> int:
    """Return the compound-pattern bonus for one prompt."""
    for pattern in CODING_COMPOUND_PATTERNS:
        if re.search(pattern, prompt_lower):
            record_reason(state, 0.75, f"Compound coding pattern: {pattern[:30]}")
            return 2
    return 0


def apply_analysis_keywords(prompt_lower: str, state: DetectionState) -> None:
    """Apply complex-analysis keyword detection."""
    score = sum(1 for keyword in ANALYSIS_KEYWORDS if keyword in prompt_lower)
    if score >= 2:
        record_reason(state, 0.65, f"Complex analysis ({score} keywords)")


# This module keeps the pattern-application pipeline separate from the mutable
# state object and public reason formatting.
# Multi-item, research, coding, and analysis passes all update the same shared
# state so the caller can make one final routing decision.
# The lower-level count and reason helpers live in task_detector_state.py.
# Coding keyword scoring also stays local so the harness decision can combine
# literal keywords with compound implementation patterns in one pass.
# That keeps the public analyzer focused on orchestration rather than scoring.
