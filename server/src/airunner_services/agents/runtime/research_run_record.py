"""Persisted record for one research run."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_run_status import (
    AgentRunStatus,
)
from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    copy_list,
    default_record_id,
    enum_value,
    utc_now_iso,
)


@dataclass(slots=True)
class ResearchRunRecord:
    """Persist one durable research run and its collected artifacts."""

    topic: str
    query: str = ""
    record_id: str = field(default_factory=default_record_id)
    status: AgentRunStatus = AgentRunStatus.PENDING
    summary: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    source_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_source(self, source_id: str) -> None:
        """Track one persisted source on the research run."""
        if source_id not in self.source_ids:
            self.source_ids.append(source_id)
            self.updated_at = utc_now_iso()

    def add_evidence(self, evidence_id: str) -> None:
        """Track one persisted evidence record on the research run."""
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)
            self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the research run to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "topic": self.topic,
            "query": self.query,
            "status": self.status.value,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_ids": copy_list(self.source_ids),
            "evidence_ids": copy_list(self.evidence_ids),
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchRunRecord":
        """Build one research run from serialized data."""
        return cls(
            topic=payload.get("topic", ""),
            query=payload.get("query", ""),
            record_id=payload.get("record_id") or default_record_id(),
            status=enum_value(
                AgentRunStatus,
                payload.get("status", AgentRunStatus.PENDING.value),
            ),
            summary=payload.get("summary", ""),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            source_ids=copy_list(payload.get("source_ids")),
            evidence_ids=copy_list(payload.get("evidence_ids")),
            metadata=copy_dict(payload.get("metadata")),
        )
