"""State and reason helpers for task-complexity detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DetectionState:
    """Mutable detection state while analyzing one prompt."""

    confidence: float = 0.0
    detected_items: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)


def record_reason(
    state: DetectionState,
    confidence: float,
    reason: str,
) -> None:
    """Update detection confidence and record one reason."""
    state.confidence = max(state.confidence, confidence)
    state.reasons.append(reason)


def matched_count(text: str) -> Optional[int]:
    """Return the first integer count embedded in one text fragment."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def matched_group_count(match: re.Match[str]) -> Optional[int]:
    """Return the first captured integer group when present."""
    if not match.groups():
        return None
    try:
        return int(match.group(1))
    except (ValueError, IndexError):
        return None


def reason_text(reasons: List[str]) -> str:
    """Return the public reason text for one detection result."""
    return "; ".join(reasons) if reasons else "Simple task, no harness needed"


# Detection state stays separate from pattern application so both the public
# analyzer and helper passes can share one mutable representation.
# Count parsing and public reason formatting also remain centralized here.
