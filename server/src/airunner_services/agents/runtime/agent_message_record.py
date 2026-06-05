"""Persisted channel message record for coding-agent runs."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_message_channel import (
    AgentMessageChannel,
)
from airunner_services.agents.runtime.agent_role import AgentRole
from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    default_record_id,
    enum_value,
    utc_now_iso,
)


@dataclass(slots=True)
class AgentMessageRecord:
    """Persist one channelled message for a coding-agent run."""

    content: str
    channel: AgentMessageChannel
    record_id: str = field(default_factory=default_record_id)
    role: AgentRole | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the message record to a JSON-compatible mapping."""
        return {
            "record_id": self.record_id,
            "channel": self.channel.value,
            "content": self.content,
            "role": self.role.value if self.role else None,
            "created_at": self.created_at,
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentMessageRecord":
        """Build a persisted message record from serialized data."""
        role_value = payload.get("role")
        return cls(
            record_id=payload.get("record_id") or default_record_id(),
            channel=enum_value(
                AgentMessageChannel,
                payload.get("channel", AgentMessageChannel.COMMENTARY.value),
            ),
            content=payload.get("content", ""),
            role=enum_value(AgentRole, role_value) if role_value else None,
            created_at=payload.get("created_at") or utc_now_iso(),
            metadata=copy_dict(payload.get("metadata")),
        )
