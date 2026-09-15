"""Persisted handoff artifact for multi-agent collaboration."""

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


@dataclass(slots=True)
class AgentHandoffRecord:
    """Persist one handoff between coding-agent roles."""

    session_id: str
    source_task_id: str
    target_task_id: str
    from_role: AgentRole
    to_role: AgentRole
    summary: str
    record_id: str = field(default_factory=default_record_id)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    artifact_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the handoff record to a JSON-compatible mapping."""
        return {
            "record_id": self.record_id,
            "session_id": self.session_id,
            "source_task_id": self.source_task_id,
            "target_task_id": self.target_task_id,
            "from_role": self.from_role.value,
            "to_role": self.to_role.value,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "artifact_paths": copy_list(self.artifact_paths),
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentHandoffRecord":
        """Build a handoff record from serialized data."""
        return cls(
            session_id=payload.get("session_id", ""),
            source_task_id=payload.get("source_task_id", ""),
            target_task_id=payload.get("target_task_id", ""),
            from_role=enum_value(
                AgentRole,
                payload.get("from_role", AgentRole.CODER.value),
            ),
            to_role=enum_value(
                AgentRole,
                payload.get("to_role", AgentRole.CODER.value),
            ),
            summary=payload.get("summary", ""),
            record_id=payload.get("record_id") or default_record_id(),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            artifact_paths=copy_list(payload.get("artifact_paths")),
            metadata=copy_dict(payload.get("metadata")),
        )