"""Review states for persisted research sources and evidence."""

from enum import Enum


class ResearchReviewStatus(str, Enum):
    """Supported states for research review artifacts."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"
