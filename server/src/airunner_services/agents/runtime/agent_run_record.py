"""Persisted agent run record with channel and tool-call history."""

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_message_channel import (
    AgentMessageChannel,
)
from airunner_services.agents.runtime.agent_message_record import (
    AgentMessageRecord,
)
from airunner_services.agents.runtime.agent_role import AgentRole
from airunner_services.agents.runtime.agent_run_status import (
    AgentRunStatus,
)
from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    default_record_id,
    enum_value,
    utc_now_iso,
)
from airunner_services.agents.runtime.agent_tool_call_record import (
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

    def compact(
        self,
        max_messages: int = 12,
        max_tool_calls: int = 20,
    ) -> None:
        """Compact older transcript history into the run summary."""
        kept_messages, omitted_messages = self._compaction_slices(
            self.messages,
            max_messages,
        )
        kept_tool_calls, omitted_tool_calls = self._compaction_slices(
            self.tool_calls,
            max_tool_calls,
        )
        if not omitted_messages and not omitted_tool_calls:
            return
        summary_parts = [part for part in [self.summary] if part]
        message_summary = self._message_compaction_summary(omitted_messages)
        tool_summary = self._tool_compaction_summary(omitted_tool_calls)
        if message_summary:
            summary_parts.append(message_summary)
        if tool_summary:
            summary_parts.append(tool_summary)
        self.summary = "\n".join(summary_parts)
        if omitted_messages:
            self.messages = kept_messages
        if omitted_tool_calls:
            self.tool_calls = kept_tool_calls
        self.metadata["compaction"] = {
            "omitted_messages": len(omitted_messages),
            "omitted_tool_calls": len(omitted_tool_calls),
            "max_messages": max_messages,
            "max_tool_calls": max_tool_calls,
            "compacted_at": utc_now_iso(),
        }
        self.updated_at = utc_now_iso()

    def channel_messages(
        self,
        channel: AgentMessageChannel,
    ) -> list[AgentMessageRecord]:
        """Return the persisted messages for one structured channel."""
        return [
            message for message in self.messages if message.channel == channel
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

    def _message_compaction_summary(
        self,
        messages: list[AgentMessageRecord],
    ) -> str:
        if not messages:
            return ""
        counts = Counter(message.channel.value for message in messages)
        channels = ", ".join(
            f"{channel}={count}" for channel, count in sorted(counts.items())
        )
        last_message = self._summary_snippet(messages[-1].content)
        return (
            f"Compacted {len(messages)} earlier messages ({channels}). "
            f"Last omitted message: {last_message}"
        )

    def _tool_compaction_summary(
        self,
        tool_calls: list[AgentToolCallRecord],
    ) -> str:
        if not tool_calls:
            return ""
        recent_tools = ", ".join(
            tool_call.tool_name for tool_call in tool_calls[-5:]
        )
        failures = sum(1 for tool_call in tool_calls if tool_call.error)
        return (
            f"Compacted {len(tool_calls)} earlier tool calls. "
            f"Recent omitted tools: {recent_tools}. "
            f"Failures among omitted calls: {failures}."
        )

    def _summary_snippet(self, content: str, limit: int = 120) -> str:
        return " ".join(content.split())[:limit]

    def _compaction_slices(
        self,
        items: list,
        max_items: int,
    ) -> tuple[list, list]:
        if max_items <= 0:
            return [], list(items)
        if len(items) <= max_items:
            return list(items), []
        return list(items[-max_items:]), list(items[:-max_items])
