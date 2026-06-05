"""Persisted audit record for one agent-generated file write."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    default_record_id,
    utc_now_iso,
)


@dataclass(slots=True)
class AgentGeneratedWriteRecord:
    """Persist one generated-write audit record for review and rollback."""

    operation: str
    summary: str
    record_id: str = field(default_factory=default_record_id)
    tool_call_id: str | None = None
    run_id: str | None = None
    root_name: str | None = None
    rel_path: str | None = None
    target_root_name: str | None = None
    target_rel_path: str | None = None
    before_exists: bool = False
    after_exists: bool = False
    before_content: str | None = None
    after_content: str | None = None
    diff: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the generated-write record to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "operation": self.operation,
            "summary": self.summary,
            "tool_call_id": self.tool_call_id,
            "run_id": self.run_id,
            "root_name": self.root_name,
            "rel_path": self.rel_path,
            "target_root_name": self.target_root_name,
            "target_rel_path": self.target_rel_path,
            "before_exists": self.before_exists,
            "after_exists": self.after_exists,
            "before_content": self.before_content,
            "after_content": self.after_content,
            "diff": self.diff,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "AgentGeneratedWriteRecord":
        """Build a generated-write record from serialized data."""
        return cls(
            operation=payload.get("operation", ""),
            summary=payload.get("summary", ""),
            record_id=payload.get("record_id") or default_record_id(),
            tool_call_id=payload.get("tool_call_id"),
            run_id=payload.get("run_id"),
            root_name=payload.get("root_name"),
            rel_path=payload.get("rel_path"),
            target_root_name=payload.get("target_root_name"),
            target_rel_path=payload.get("target_rel_path"),
            before_exists=bool(payload.get("before_exists")),
            after_exists=bool(payload.get("after_exists")),
            before_content=payload.get("before_content"),
            after_content=payload.get("after_content"),
            diff=payload.get("diff", ""),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            metadata=copy_dict(payload.get("metadata")),
        )
