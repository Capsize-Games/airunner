"""Persisted structured brief package for one research run."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    copy_list,
    default_record_id,
    utc_now_iso,
)


@dataclass(slots=True)
class ResearchBriefRecord:
    """Persist one stable brief package generated from research evidence."""

    run_id: str
    title: str
    executive_summary: str
    supported_findings: list[str]
    open_questions: list[str]
    weak_evidence_ids: list[str]
    coverage_score: float
    confidence_score: float
    record_id: str = field(default_factory=default_record_id)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    artifact_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the brief package to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "title": self.title,
            "executive_summary": self.executive_summary,
            "supported_findings": copy_list(self.supported_findings),
            "open_questions": copy_list(self.open_questions),
            "weak_evidence_ids": copy_list(self.weak_evidence_ids),
            "coverage_score": self.coverage_score,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "artifact_paths": copy_list(self.artifact_paths),
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchBriefRecord":
        """Build one brief package from serialized data."""
        return cls(
            run_id=payload.get("run_id", ""),
            title=payload.get("title", ""),
            executive_summary=payload.get("executive_summary", ""),
            supported_findings=copy_list(payload.get("supported_findings")),
            open_questions=copy_list(payload.get("open_questions")),
            weak_evidence_ids=copy_list(payload.get("weak_evidence_ids")),
            coverage_score=float(payload.get("coverage_score", 0.0)),
            confidence_score=float(payload.get("confidence_score", 0.0)),
            record_id=payload.get("record_id") or default_record_id(),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            artifact_paths=copy_list(payload.get("artifact_paths")),
            metadata=copy_dict(payload.get("metadata")),
        )