"""Review states for meeting-derived deliverable packs."""

from enum import Enum


class MeetingReviewStatus(str, Enum):
    """Supported review states for meeting deliverables."""

    PENDING = "pending"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"