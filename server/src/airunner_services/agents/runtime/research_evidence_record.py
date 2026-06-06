"""Persisted evidence records for one research run."""

from dataclasses import dataclass, field
from typing import Any

from airunner_services.agents.runtime.agent_runtime_support import (
    copy_dict,
    copy_list,
    default_record_id,
    enum_value,
    utc_now_iso,
)
from airunner_services.agents.runtime.research_review_status import (
    ResearchReviewStatus,
)


@dataclass(slots=True)
class ResearchEvidenceRecord:
    """Persist one attributed fact, quote, or numeric finding."""

    run_id: str
    fact_text: str
    source_ids: list[str]
    record_id: str = field(default_factory=default_record_id)
    status: ResearchReviewStatus = ResearchReviewStatus.UNRESOLVED
    evidence_kind: str = "claim"
    confidence: str = "medium"
    quote_text: str = ""
    numeric_value: str = ""
    numeric_unit: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the evidence record to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "fact_text": self.fact_text,
            "source_ids": copy_list(self.source_ids),
            "status": self.status.value,
            "evidence_kind": self.evidence_kind,
            "confidence": self.confidence,
            "quote_text": self.quote_text,
            "numeric_value": self.numeric_value,
            "numeric_unit": self.numeric_unit,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "ResearchEvidenceRecord":
        """Build one evidence record from serialized data."""
        return cls(
            run_id=payload.get("run_id", ""),
            fact_text=payload.get("fact_text", ""),
            source_ids=copy_list(payload.get("source_ids")),
            record_id=payload.get("record_id") or default_record_id(),
            status=enum_value(
                ResearchReviewStatus,
                payload.get(
                    "status",
                    ResearchReviewStatus.UNRESOLVED.value,
                ),
            ),
            evidence_kind=payload.get("evidence_kind", "claim"),
            confidence=payload.get("confidence", "medium"),
            quote_text=payload.get("quote_text", ""),
            numeric_value=payload.get("numeric_value", ""),
            numeric_unit=payload.get("numeric_unit", ""),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            metadata=copy_dict(payload.get("metadata")),
        )
