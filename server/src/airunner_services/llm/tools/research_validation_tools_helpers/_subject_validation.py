"""Subject validation helpers for research tools."""

import re

OBITUARY_PATTERNS = [
    r"passed away",
    r"died on",
    r"in memoriam",
    r"obituary",
    r"funeral",
    r"survived by",
]


def validate_research_subject_impl(
    content: str,
    subject_name: str,
    expected_context: str = "",
) -> dict:
    """Validate that content matches the intended research subject."""
    if not content or not subject_name:
        return _missing_subject_result()
    content_lower = content.lower()
    reasons, red_flags = _name_match_findings(content_lower, subject_name)
    red_flags.extend(_obituary_flags(content_lower))
    context_reasons, context_flags = _expected_context_findings(
        content_lower,
        expected_context,
    )
    reasons.extend(context_reasons)
    red_flags.extend(context_flags)
    likely_match, confidence = _confidence_from_findings(reasons, red_flags)
    return {
        "likely_match": likely_match,
        "confidence": confidence,
        "reasons": reasons,
        "red_flags": red_flags,
    }


def _missing_subject_result() -> dict:
    """Return the default payload for missing subject validation input."""
    return {
        "likely_match": False,
        "confidence": "uncertain",
        "reasons": ["Missing content or subject name"],
        "red_flags": [],
    }


def _name_match_findings(content_lower: str, subject_name: str) -> tuple[list[str], list[str]]:
    """Return findings based on direct or partial subject-name matches."""
    name_lower = subject_name.lower()
    name_parts = name_lower.split()
    if name_lower in content_lower:
        return [f"Full name '{subject_name}' found in content"], []
    parts_found = sum(1 for part in name_parts if part in content_lower)
    if parts_found >= len(name_parts) - 1:
        return [f"Name parts found ({parts_found}/{len(name_parts)})"], []
    return [], ["Name not clearly found in content"]


def _obituary_flags(content_lower: str) -> list[str]:
    """Return obituary-style red flags when the content looks unrelated."""
    for pattern in OBITUARY_PATTERNS:
        if re.search(pattern, content_lower):
            return ["Content appears to be an obituary - verify correct person"]
    return []


def _expected_context_findings(
    content_lower: str,
    expected_context: str,
) -> tuple[list[str], list[str]]:
    """Return findings based on expected contextual terms."""
    if not expected_context:
        return [], []
    context_terms = [term.strip() for term in expected_context.lower().split(",")]
    reasons = [f"Context match: '{term}'" for term in context_terms if term in content_lower]
    if reasons:
        return reasons, []
    return [], [f"Expected context not found: {expected_context}"]


def _confidence_from_findings(
    reasons: list[str],
    red_flags: list[str],
) -> tuple[bool, str]:
    """Return the likely-match and confidence labels for the findings."""
    if len(red_flags) >= 2:
        return False, "low"
    if len(red_flags) == 1:
        return len(reasons) >= 2, "medium"
    if len(reasons) >= 2:
        return True, "high"
    return len(reasons) > 0, "medium"