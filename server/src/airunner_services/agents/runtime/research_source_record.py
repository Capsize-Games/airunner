"""Persisted source metadata for one research run."""

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
class ResearchSourceRecord:
    """Persist one research source and its review metadata."""

    run_id: str
    url: str
    title: str = ""
    record_id: str = field(default_factory=default_record_id)
    status: ResearchReviewStatus = ResearchReviewStatus.UNRESOLVED
    source_type: str = "web"
    excerpt: str = ""
    published_at: str = ""
    retrieved_at: str = field(default_factory=utc_now_iso)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    authors: list[str] = field(default_factory=list)
    failure_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the source record to JSON-compatible data."""
        return {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "url": self.url,
            "title": self.title,
            "status": self.status.value,
            "source_type": self.source_type,
            "excerpt": self.excerpt,
            "published_at": self.published_at,
            "retrieved_at": self.retrieved_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "authors": copy_list(self.authors),
            "failure_reason": self.failure_reason,
            "metadata": copy_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchSourceRecord":
        """Build one source record from serialized data."""
        return cls(
            run_id=payload.get("run_id", ""),
            url=payload.get("url", ""),
            title=payload.get("title", ""),
            record_id=payload.get("record_id") or default_record_id(),
            status=enum_value(
                ResearchReviewStatus,
                payload.get(
                    "status",
                    ResearchReviewStatus.UNRESOLVED.value,
                ),
            ),
            source_type=payload.get("source_type", "web"),
            excerpt=payload.get("excerpt", ""),
            published_at=payload.get("published_at", ""),
            retrieved_at=payload.get("retrieved_at") or utc_now_iso(),
            created_at=payload.get("created_at") or utc_now_iso(),
            updated_at=payload.get("updated_at") or utc_now_iso(),
            authors=copy_list(payload.get("authors")),
            failure_reason=payload.get("failure_reason", ""),
            metadata=copy_dict(payload.get("metadata")),
        )