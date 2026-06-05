"""Task complexity detection for automatic harness application.

This module detects when a user's request should be wrapped with the
Long-Running Harness for better coherency and progress tracking.

The harness is automatically applied for:
- Multi-step tasks (e.g., "research 5 papers", "implement these features")
- Research projects (e.g., "investigate X and write a report")
- Any task with explicit multiple items or steps

This follows Anthropic's pattern of using a harness to maintain coherency
during complex multi-step tasks within a session.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from airunner_services.llm.long_running.task_detector_helpers import (
    apply_analysis_keywords,
    apply_coding_patterns,
    apply_multi_item_patterns,
    apply_research_patterns,
)
from airunner_services.llm.long_running.task_detector_state import (
    DetectionState,
    reason_text,
)
from airunner_services.llm.long_running.task_detector_patterns import (
    MULTI_STEP_KEYWORDS,
)


class TaskType(Enum):
    """Types of tasks that benefit from harness wrapping."""

    SIMPLE = "simple"  # No harness needed
    MULTI_RESEARCH = "multi_research"  # Multiple research topics
    CODING_PROJECT = "coding_project"  # Legacy compatibility value
    MULTI_STEP = "multi_step"  # Explicit numbered/listed steps
    COMPLEX_ANALYSIS = "complex_analysis"  # Deep analysis tasks


@dataclass
class TaskAnalysis:
    """Result of analyzing a user prompt for task complexity."""

    task_type: TaskType
    should_use_harness: bool
    detected_items: List[str]  # Individual tasks/topics detected
    confidence: float  # 0.0 to 1.0
    reason: str  # Human-readable explanation


REASON_TASK_TYPES = [
    ("research", TaskType.MULTI_RESEARCH),
    ("implementation", TaskType.MULTI_STEP),
    ("multi-step", TaskType.MULTI_STEP),
    ("analysis", TaskType.COMPLEX_ANALYSIS),
]


def analyze_task(prompt: str) -> TaskAnalysis:
    """Analyze one prompt to determine if it needs harness wrapping."""
    prompt_lower = prompt.lower()
    state = DetectionState()
    apply_multi_item_patterns(prompt_lower, state)
    apply_research_patterns(prompt_lower, state)
    apply_coding_patterns(prompt_lower, state)
    _apply_first_keyword_match(
        prompt_lower, MULTI_STEP_KEYWORDS, state, 0.6, "Multi-step keyword"
    )
    apply_analysis_keywords(prompt_lower, state)
    _apply_comma_list(prompt, state)
    task_type = _determine_task_type(prompt_lower, state)
    should_use_harness = (
        state.confidence >= 0.6 and task_type != TaskType.SIMPLE
    )
    return TaskAnalysis(
        task_type=task_type,
        should_use_harness=should_use_harness,
        detected_items=state.detected_items,
        confidence=state.confidence,
        reason=reason_text(state.reasons),
    )


def _apply_first_keyword_match(
    prompt_lower: str,
    keywords: List[str],
    state: DetectionState,
    confidence: float,
    label: str,
) -> None:
    """Apply the first matching regex keyword from one list."""
    for keyword in keywords:
        if re.search(keyword, prompt_lower):
            state.confidence = max(state.confidence, confidence)
            state.reasons.append(f"{label}: {keyword}")
            return


def _apply_comma_list(prompt: str, state: DetectionState) -> None:
    """Apply comma-list detection to one prompt."""
    comma_items = _extract_comma_list(prompt)
    if len(comma_items) >= 3:
        state.confidence = max(state.confidence, 0.75)
        state.reasons.append(f"Comma-separated list: {len(comma_items)} items")
        state.detected_items = comma_items


def _extract_comma_list(prompt: str) -> List[str]:
    """Extract items from a comma-separated list in the prompt.

    Args:
        prompt: User's input text

    Returns:
        List of extracted items
    """
    # Look for patterns like "research X, Y, and Z" or "implement A, B, C"
    patterns = [
        r"(?:research|implement|analyze|compare|write about|investigate)\s+(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            items_str = match.group(1)
            # First, handle "and" separately to avoid "and X" in results
            # Replace ", and " with just ","
            items_str = re.sub(r",\s*and\s+", ", ", items_str)
            # Replace standalone " and " with ","
            items_str = re.sub(r"\s+and\s+", ", ", items_str)
            # Now split by comma
            items = re.split(r",\s*", items_str)
            # Clean up items
            items = [item.strip() for item in items if item.strip()]
            # Filter out items that are too short or look like noise
            items = [
                item
                for item in items
                if len(item) > 2 and item.lower() not in ["the", "a", "an"]
            ]
            if len(items) >= 2:
                return items[:10]  # Cap at 10 items

    return []


def _determine_task_type(
    prompt_lower: str,
    state: DetectionState,
) -> TaskType:
    """Determine the specific type of task.

    Args:
        prompt_lower: Lowercased prompt
        confidence: Current confidence score
        reasons: List of detection reasons

    Returns:
        TaskType enum value
    """
    if state.confidence < 0.5:
        return TaskType.SIMPLE

    for keyword, task_type in REASON_TASK_TYPES:
        if _reasons_contain(state.reasons, keyword):
            return task_type
    if "research" in prompt_lower or "paper" in prompt_lower:
        return TaskType.MULTI_RESEARCH
    return TaskType.MULTI_STEP


def _reasons_contain(reasons: List[str], keyword: str) -> bool:
    """Return whether any recorded reason contains one keyword."""
    return any(keyword in reason.lower() for reason in reasons)


def should_use_harness(prompt: str) -> Tuple[bool, Optional[TaskAnalysis]]:
    """Quick check if a prompt should use the harness.

    Args:
        prompt: User's input text

    Returns:
        Tuple of (should_use, analysis) - analysis is None if not using harness
    """
    analysis = analyze_task(prompt)
    if analysis.should_use_harness:
        return True, analysis
    return False, None
