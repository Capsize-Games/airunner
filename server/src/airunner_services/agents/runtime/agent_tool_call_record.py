"""Persisted tool execution record for coding-agent runs."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    default_record_id,
    utc_now_iso,
)


@dataclass(slots=True)
class AgentToolCallRecord:
    """Persist one tool call and its result or failure."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    record_id: str = field(default_factory=default_record_id)
    output: Any = None
    error: str | None = None
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the tool-call record to a JSON-compatible mapping."""
        return {
            "record_id": self.record_id,
            "tool_name": self.tool_name,
            "arguments": copy_dict(self.arguments),
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentToolCallRecord":
        """Build a persisted tool-call record from serialized data."""
        return cls(
            record_id=payload.get("record_id") or default_record_id(),
            tool_name=payload.get("tool_name", ""),
            arguments=copy_dict(payload.get("arguments")),
            output=payload.get("output"),
            error=payload.get("error"),
            started_at=payload.get("started_at") or utc_now_iso(),
            finished_at=payload.get("finished_at"),
        )
