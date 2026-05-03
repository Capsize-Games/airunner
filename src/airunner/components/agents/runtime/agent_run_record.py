"""Persisted agent run record with channel and tool-call history."""

from dataclasses import dataclass, field
from typing import Any

from airunner.components.agents.runtime.agent_message_channel import (
    AgentMessageChannel,
)
from airunner.components.agents.runtime.agent_message_record import (
    AgentMessageRecord,
)
from airunner.components.agents.runtime.agent_role import AgentRole
from airunner.components.agents.runtime.agent_run_status import (
    AgentRunStatus,
)
from airunner.components.agents.runtime.agent_runtime_support import (
    copy_dict,
    default_record_id,
    enum_value,
    utc_now_iso,
)
from airunner.components.agents.runtime.agent_tool_call_record import (
    AgentToolCallRecord,
)


@dataclass(slots=True)
class AgentRunRecord:
    """Persist one coding-agent run and its durable transcript."""

    session_id: str
    task_id: str
    role: AgentRole
    record_id: str = field(default_factory=default_record_id)
    status: AgentRunStatus = AgentRunStatus.PENDING
    summary: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    messages: list[AgentMessageRecord] = field(default_factory=list)
    tool_calls: list[AgentToolCallRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: AgentMessageRecord) -> None:
        """Append a message to the persisted run transcript."""
        self.messages.append(message)
        self.updated_at = utc_now_iso()

    def add_tool_call(self, tool_call: AgentToolCallRecord) -> None:
        """Append a tool call to the persisted run audit trail."""
        self.tool_calls.append(tool_call)
        self.updated_at = utc_now_iso()

    def channel_messages(
        self,
        channel: AgentMessageChannel,
    ) -> list[AgentMessageRecord]:
        """Return the persisted messages for one structured channel."""
        return [
            message
            for message in self.messages
            if message.channel == channel
        ]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the run record to a JSON-compatible mapping."""
        return {
            "record_id": self.record_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "role": self.role.value,
            "status": self.status.value,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [message.to_dict() for message in self.messages],
            "tool_calls": [
                tool_call.to_dict() for tool_call in self.tool_calls
            ],
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentRunRecord":
        """Build a persisted run record from serialized data."""
        messages = [
            AgentMessageRecord.from_dict(item)
            for item in payload.get("messages", [])
        ]
        tool_calls = [
            AgentToolCallRecord.from_dict(item)
            for item in payload.get("tool_calls", [])
        ]
        return cls(
            record_id=payload.get("record_id") or default_record_id(),
            session_id=payload.get("session_id", ""),
            task_id=payload.get("task_id", ""),
            role=enum_value(
                AgentRole,
                payload.get("role", AgentRole.CODER.value),
            ),
            status=enum_value(
                AgentRunStatus,
                payload.get("status", AgentRunStatus.PENDING.value),
            ),
            summary=payload.get("summary", ""),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            messages=messages,
            tool_calls=tool_calls,
            metadata=copy_dict(payload.get("metadata")),
        )