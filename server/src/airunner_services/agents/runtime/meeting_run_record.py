"""Persisted normalized input and metadata for one meeting run."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    copy_list,
    default_record_id,
    utc_now_iso,
)


@dataclass(slots=True)
class MeetingRunRecord:
    """Persist one meeting ingestion run and normalized source text."""

    title: str
    raw_input: str
    normalized_input: str
    source_kind: str = "transcript"
    record_id: str = field(default_factory=default_record_id)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    participants: list[str] = field(default_factory=list)
    item_ids: list[str] = field(default_factory=list)
    deliverable_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_item(self, item_id: str) -> None:
        """Attach one extracted meeting item to this run."""
        if item_id not in self.item_ids:
            self.item_ids.append(item_id)
            self.updated_at = utc_now_iso()

    def add_deliverable(self, deliverable_id: str) -> None:
        """Attach one deliverable pack to this run."""
        if deliverable_id not in self.deliverable_ids:
            self.deliverable_ids.append(deliverable_id)
            self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the meeting run to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "title": self.title,
            "raw_input": self.raw_input,
            "normalized_input": self.normalized_input,
            "source_kind": self.source_kind,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "participants": copy_list(self.participants),
            "item_ids": copy_list(self.item_ids),
            "deliverable_ids": copy_list(self.deliverable_ids),
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MeetingRunRecord":
        """Build one meeting run from serialized data."""
        return cls(
            title=payload.get("title", ""),
            raw_input=payload.get("raw_input", ""),
            normalized_input=payload.get("normalized_input", ""),
            source_kind=payload.get("source_kind", "transcript"),
            record_id=payload.get("record_id") or default_record_id(),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            participants=copy_list(payload.get("participants")),
            item_ids=copy_list(payload.get("item_ids")),
            deliverable_ids=copy_list(payload.get("deliverable_ids")),
            metadata=copy_dict(payload.get("metadata")),
        )
