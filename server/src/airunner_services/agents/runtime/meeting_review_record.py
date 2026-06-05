"""Persisted review pass for one meeting deliverable pack."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    copy_list,
    default_record_id,
    enum_value,
    utc_now_iso,
)
from airunner_services.agents.runtime.meeting_review_status import (
    MeetingReviewStatus,
)


@dataclass(slots=True)
class MeetingReviewRecord:
    """Persist one review pass, corrections, and approval outcome."""

    run_id: str
    deliverable_id: str
    reviewer_notes: str = ""
    review_status: MeetingReviewStatus = MeetingReviewStatus.PENDING
    flagged_item_ids: list[str] = field(default_factory=list)
    approved_item_ids: list[str] = field(default_factory=list)
    correction_records: list[dict[str, Any]] = field(default_factory=list)
    record_id: str = field(default_factory=default_record_id)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    artifact_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the review pass to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "deliverable_id": self.deliverable_id,
            "reviewer_notes": self.reviewer_notes,
            "review_status": self.review_status.value,
            "flagged_item_ids": copy_list(self.flagged_item_ids),
            "approved_item_ids": copy_list(self.approved_item_ids),
            "correction_records": copy_list(self.correction_records),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "artifact_paths": copy_list(self.artifact_paths),
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MeetingReviewRecord":
        """Build one meeting review record from serialized data."""
        return cls(
            run_id=payload.get("run_id", ""),
            deliverable_id=payload.get("deliverable_id", ""),
            reviewer_notes=payload.get("reviewer_notes", ""),
            review_status=enum_value(
                MeetingReviewStatus,
                payload.get(
                    "review_status",
                    MeetingReviewStatus.PENDING.value,
                ),
            ),
            flagged_item_ids=copy_list(payload.get("flagged_item_ids")),
            approved_item_ids=copy_list(payload.get("approved_item_ids")),
            correction_records=copy_list(payload.get("correction_records")),
            record_id=payload.get("record_id") or default_record_id(),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            artifact_paths=copy_list(payload.get("artifact_paths")),
            metadata=copy_dict(payload.get("metadata")),
        )
