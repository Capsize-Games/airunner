"""Persisted structured extraction item for one meeting run."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    default_record_id,
    enum_value,
    utc_now_iso,
)
from airunner_services.agents.runtime.meeting_item_status import (
    MeetingItemStatus,
)


@dataclass(slots=True)
class MeetingItemRecord:
    """Persist one decision, task, risk, or question from a meeting."""

    run_id: str
    item_kind: str
    summary: str
    source_excerpt: str
    record_id: str = field(default_factory=default_record_id)
    status: MeetingItemStatus = MeetingItemStatus.UNRESOLVED
    confidence: str = "medium"
    speaker: str = ""
    owner: str = ""
    due_date: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the meeting item to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "item_kind": self.item_kind,
            "summary": self.summary,
            "source_excerpt": self.source_excerpt,
            "status": self.status.value,
            "confidence": self.confidence,
            "speaker": self.speaker,
            "owner": self.owner,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MeetingItemRecord":
        """Build one meeting item from serialized data."""
        return cls(
            run_id=payload.get("run_id", ""),
            item_kind=payload.get("item_kind", ""),
            summary=payload.get("summary", ""),
            source_excerpt=payload.get("source_excerpt", ""),
            record_id=payload.get("record_id") or default_record_id(),
            status=enum_value(
                MeetingItemStatus,
                payload.get(
                    "status",
                    MeetingItemStatus.UNRESOLVED.value,
                ),
            ),
            confidence=payload.get("confidence", "medium"),
            speaker=payload.get("speaker", ""),
            owner=payload.get("owner", ""),
            due_date=payload.get("due_date", ""),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            metadata=copy_dict(payload.get("metadata")),
        )
