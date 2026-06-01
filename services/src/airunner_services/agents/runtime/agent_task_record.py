"""Persisted task ledger item for coding-agent work."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_role import AgentRole
from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    copy_list,
    default_record_id,
    enum_value,
    utc_now_iso,
)
from airunner_services.agents.runtime.agent_task_status import (
    AgentTaskStatus,
)


@dataclass(slots=True)
class AgentTaskRecord:
    """Persist one task in the project task ledger."""

    title: str
    role: AgentRole
    session_id: str
    record_id: str = field(default_factory=default_record_id)
    description: str = ""
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    artifact_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task record to a JSON-compatible mapping."""
        return {
            "record_id": self.record_id,
            "title": self.title,
            "description": self.description,
            "role": self.role.value,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "artifact_paths": copy_list(self.artifact_paths),
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentTaskRecord":
        """Build a persisted task record from serialized data."""
        return cls(
            record_id=payload.get("record_id") or default_record_id(),
            title=payload.get("title", ""),
            description=payload.get("description", ""),
            role=enum_value(
                AgentRole,
                payload.get("role", AgentRole.CODER.value),
            ),
            session_id=payload.get("session_id", ""),
            status=enum_value(
                AgentTaskStatus,
                payload.get("status", AgentTaskStatus.PENDING.value),
            ),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            artifact_paths=copy_list(payload.get("artifact_paths")),
            metadata=copy_dict(payload.get("metadata")),
        )