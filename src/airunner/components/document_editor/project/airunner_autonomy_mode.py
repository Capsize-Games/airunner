"""Autonomy modes for AIRunner coding projects."""

from enum import Enum


class AirunnerAutonomyMode(str, Enum):
    """Supported autonomy modes for an AIRunner coding project."""

    REVIEW_FIRST = "review-first"
    MIXED = "mixed"
    FULL_AUTONOMY = "full-autonomy"