"""Status values for structured meeting extraction items."""

from enum import Enum


class MeetingItemStatus(str, Enum):
    """Supported states for meeting-derived items."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CONFLICTING = "conflicting"
    UNRESOLVED = "unresolved"
