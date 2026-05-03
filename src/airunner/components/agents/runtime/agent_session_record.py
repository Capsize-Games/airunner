"""Persisted project session record for coding-agent work."""

from dataclasses import dataclass, field
from typing import Any

from airunner.components.agents.runtime.agent_run_status import (
    AgentRunStatus,
)
from airunner.components.agents.runtime.agent_runtime_support import (
    copy_dict,
    copy_list,
    default_record_id,
    enum_value,
    utc_now_iso,
)


@dataclass(slots=True)
class AgentSessionRecord:
    """Persist one coding-agent session for restart recovery."""

    project_path: str
    title: str
    record_id: str = field(default_factory=default_record_id)
    status: AgentRunStatus = AgentRunStatus.PENDING
    active_run_id: str | None = None
    task_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the session record to a JSON-compatible mapping."""
        return {
            "record_id": self.record_id,
            "project_path": self.project_path,
            "title": self.title,
            "status": self.status.value,
            "active_run_id": self.active_run_id,
            "task_ids": copy_list(self.task_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentSessionRecord":
        """Build a persisted session record from serialized data."""
        return cls(
            record_id=payload.get("record_id") or default_record_id(),
            project_path=payload.get("project_path", ""),
            title=payload.get("title", ""),
            status=enum_value(
                AgentRunStatus,
                payload.get("status", AgentRunStatus.PENDING.value),
            ),
            active_run_id=payload.get("active_run_id"),
            task_ids=copy_list(payload.get("task_ids")),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            metadata=copy_dict(payload.get("metadata")),
        )