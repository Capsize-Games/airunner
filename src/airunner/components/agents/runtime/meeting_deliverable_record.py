"""Persisted deliverable pack derived from structured meeting state."""

from dataclasses import dataclass, field
from typing import Any

from airunner.components.agents.runtime.agent_runtime_support import (
    copy_dict,
    copy_list,
    default_record_id,
    utc_now_iso,
)


@dataclass(slots=True)
class MeetingDeliverableRecord:
    """Persist one deliverable pack generated from meeting items."""

    run_id: str
    title: str
    action_items: list[str]
    decision_log: list[str]
    follow_up_points: list[str]
    unresolved_items: list[str]
    record_id: str = field(default_factory=default_record_id)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    artifact_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the deliverable pack to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "title": self.title,
            "action_items": copy_list(self.action_items),
            "decision_log": copy_list(self.decision_log),
            "follow_up_points": copy_list(self.follow_up_points),
            "unresolved_items": copy_list(self.unresolved_items),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "artifact_paths": copy_list(self.artifact_paths),
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "MeetingDeliverableRecord":
        """Build one deliverable pack from serialized data."""
        return cls(
            run_id=payload.get("run_id", ""),
            title=payload.get("title", ""),
            action_items=copy_list(payload.get("action_items")),
            decision_log=copy_list(payload.get("decision_log")),
            follow_up_points=copy_list(payload.get("follow_up_points")),
            unresolved_items=copy_list(payload.get("unresolved_items")),
            record_id=payload.get("record_id") or default_record_id(),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            artifact_paths=copy_list(payload.get("artifact_paths")),
            metadata=copy_dict(payload.get("metadata")),
        )