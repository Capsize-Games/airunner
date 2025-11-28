"""Task complexity detection for automatic harness application.

This module detects when a user's request should be wrapped with the
Long-Running Harness for better coherency and progress tracking.

The harness is automatically applied for:
- Multi-step tasks (e.g., "research 5 papers", "implement these features")
- Complex coding tasks (e.g., "refactor this module", "add tests for X")
- Research projects (e.g., "investigate X and write a report")
- Any task with explicit multiple items or steps

This follows Anthropic's pattern of using a harness to maintain coherency
during complex multi-step tasks within a session.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class TaskType(Enum):
    """Types of tasks that benefit from harness wrapping."""

    SIMPLE = "simple"  # No harness needed
    MULTI_RESEARCH = "multi_research"  # Multiple research topics
    CODING_PROJECT = "coding_project"  # Code implementation/refactoring
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


# Patterns that indicate multiple items
MULTI_ITEM_PATTERNS = [
    # Explicit numbers: "research 5 papers", "implement 3 features", "write 3 papers"
    r"(\d+)\s+(papers?|topics?|items?|features?|functions?|tests?|files?|endpoints?|components?|modules?|reports?|articles?)",
    # "write X papers/reports" pattern
    r"write\s+(\d+)\s+(?:research\s+)?(?:papers?|reports?|articles?)",
    # Lists with "and": "research X, Y, and Z"
    r"research\s+.+(?:,\s*.+)+(?:,?\s+and\s+.+)",
    # Explicit lists: "the following: 1. X 2. Y"
    r"(?:following|these)[:.]?\s*(?:\d+[.)]\s*.+){2,}",
    # Bullet points
    r"[-•]\s*.+(?:\n[-•]\s*.+)+",
]

# Keywords indicating coding projects
CODING_PROJECT_KEYWORDS = [
    "implement",
    "refactor",
    "build",
    "create",
    "develop",
    "add feature",
    "add test",
    "write test",
    "unit test",
    "fix bug",
    "debug",
    "optimize",
    "migrate",
    "upgrade",
    "port",
    "convert",
    "integrate",
]

# Compound patterns that indicate coding projects (require fewer matches)
CODING_COMPOUND_PATTERNS = [
    r"refactor.*and.*(?:add|write|create)",  # "refactor X and add Y"
    r"(?:add|write|create).*(?:test|feature).*and",  # "add tests and..."
    r"implement.*(?:with|including).*test",  # "implement X with tests"
]

# Keywords indicating multi-step tasks
MULTI_STEP_KEYWORDS = [
    "step by step",
    "steps",
    "first.*then",
    "after that",
    "following steps",
    "process",
    "workflow",
    "pipeline",
]

# Keywords indicating complex analysis
ANALYSIS_KEYWORDS = [
    "analyze",
    "investigate",
    "compare",
    "evaluate",
    "assess",
    "review",
    "audit",
    "examine",
    "comprehensive",
    "thorough",
    "in-depth",
    "detailed analysis",
]

# Research-specific patterns
RESEARCH_PATTERNS = [
    r"research\s+(\d+)",  # "research 5 papers"
    r"write\s+(\d+)\s+(?:papers?|reports?|articles?)",
    r"investigate\s+(?:multiple|several|\d+)",
    r"compare\s+(?:multiple|several|\d+)",
]


def analyze_task(prompt: str) -> TaskAnalysis:
    """Analyze a prompt to determine if it needs harness wrapping.

    Args:
        prompt: User's input text

    Returns:
        TaskAnalysis with detection results
    """
    prompt_lower = prompt.lower()
    detected_items = []
    confidence = 0.0
    reasons = []

    # Check for explicit multiple items (highest confidence)
    for pattern in MULTI_ITEM_PATTERNS:
        match = re.search(pattern, prompt_lower)
        if match:
            confidence = max(confidence, 0.9)
            reasons.append(f"Explicit multi-item pattern: {match.group(0)[:50]}")
            # Try to extract count
            count_match = re.search(r"(\d+)", match.group(0))
            if count_match:
                count = int(count_match.group(1))
                detected_items = [f"item_{i+1}" for i in range(count)]

    # Check for research patterns
    for pattern in RESEARCH_PATTERNS:
        match = re.search(pattern, prompt_lower)
        if match:
            confidence = max(confidence, 0.85)
            reasons.append(f"Research pattern detected: {match.group(0)}")
            if match.groups():
                try:
                    count = int(match.group(1))
                    detected_items = [f"research_topic_{i+1}" for i in range(count)]
                except (ValueError, IndexError):
                    pass

    # Check for coding project keywords
    coding_score = sum(
        1 for kw in CODING_PROJECT_KEYWORDS if kw in prompt_lower
    )
    
    # Check for compound coding patterns (these are strong signals)
    for pattern in CODING_COMPOUND_PATTERNS:
        if re.search(pattern, prompt_lower):
            confidence = max(confidence, 0.75)
            reasons.append(f"Compound coding pattern: {pattern[:30]}")
            coding_score += 2  # Boost the score
            break
    
    if coding_score >= 2:
        confidence = max(confidence, 0.7)
        reasons.append(f"Multiple coding keywords ({coding_score})")
    elif coding_score == 1:
        confidence = max(confidence, 0.4)
        reasons.append("Single coding keyword")

    # Check for multi-step keywords
    for kw in MULTI_STEP_KEYWORDS:
        if re.search(kw, prompt_lower):
            confidence = max(confidence, 0.6)
            reasons.append(f"Multi-step keyword: {kw}")
            break

    # Check for analysis keywords
    analysis_score = sum(1 for kw in ANALYSIS_KEYWORDS if kw in prompt_lower)
    if analysis_score >= 2:
        confidence = max(confidence, 0.65)
        reasons.append(f"Complex analysis ({analysis_score} keywords)")

    # Check for comma-separated lists (e.g., "research X, Y, Z")
    comma_items = _extract_comma_list(prompt)
    if len(comma_items) >= 3:
        confidence = max(confidence, 0.75)
        reasons.append(f"Comma-separated list: {len(comma_items)} items")
        detected_items = comma_items

    # Determine task type
    task_type = _determine_task_type(prompt_lower, confidence, reasons)

    # Decide if harness should be used
    should_use_harness = confidence >= 0.6 and task_type != TaskType.SIMPLE

    return TaskAnalysis(
        task_type=task_type,
        should_use_harness=should_use_harness,
        detected_items=detected_items,
        confidence=confidence,
        reason="; ".join(reasons) if reasons else "Simple task, no harness needed",
    )


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
    prompt_lower: str, confidence: float, reasons: List[str]
) -> TaskType:
    """Determine the specific type of task.

    Args:
        prompt_lower: Lowercased prompt
        confidence: Current confidence score
        reasons: List of detection reasons

    Returns:
        TaskType enum value
    """
    if confidence < 0.5:
        return TaskType.SIMPLE

    # Check specific types
    if any("research" in r.lower() for r in reasons):
        return TaskType.MULTI_RESEARCH

    if any("coding" in r.lower() for r in reasons):
        return TaskType.CODING_PROJECT

    if any("multi-step" in r.lower() for r in reasons):
        return TaskType.MULTI_STEP

    if any("analysis" in r.lower() for r in reasons):
        return TaskType.COMPLEX_ANALYSIS

    # Default based on keywords in prompt
    if "research" in prompt_lower or "paper" in prompt_lower:
        return TaskType.MULTI_RESEARCH
    if any(kw in prompt_lower for kw in CODING_PROJECT_KEYWORDS[:5]):
        return TaskType.CODING_PROJECT

    return TaskType.MULTI_STEP


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
