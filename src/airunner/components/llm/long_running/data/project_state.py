"""Local DTOs and resource helpers for long-running project state."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from airunner.daemon_client.resource_store import (
    GuiResourceStore,
    ResourceRecord,
    get_resource_store,
)


class ProjectStatus(str, Enum):
    """Status of a long-running project."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class FeatureStatus(str, Enum):
    """Status of a project feature."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    FAILING = "failing"
    PASSING = "passing"
    BLOCKED = "blocked"


class FeatureCategory(str, Enum):
    """Category of feature for routing to specialized agents."""

    FUNCTIONAL = "functional"
    UI = "ui"
    INTEGRATION = "integration"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    SECURITY = "security"


class DecisionOutcome(str, Enum):
    """Outcome of a past decision."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    REVERTED = "reverted"


def _enum_value(value: Any) -> Any:
    """Return the primitive value for enum-like fields."""
    return getattr(value, "value", value)


def _timestamp(value: Any) -> Optional[datetime]:
    """Convert an ISO string or datetime-like value into datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


class ProjectState(ResourceRecord):
    """Project DTO backed by one workspace resource record."""

    def __init__(self, values: Optional[dict[str, Any]] = None) -> None:
        super().__init__("ProjectState", values)

    def get_progress_summary(self) -> str:
        """Get a human-readable progress summary."""
        total = int(getattr(self, "total_features", 0) or 0)
        passing = int(getattr(self, "passing_features", 0) or 0)
        if total == 0:
            return "Project not yet initialized"
        pct = (passing / total) * 100
        return f"{passing}/{total} features passing ({pct:.1f}%)"

    def to_context_dict(self) -> dict[str, Any]:
        """Export key project info for agent context."""
        return {
            "project_name": getattr(self, "name", None),
            "description": getattr(self, "description", None),
            "status": _enum_value(getattr(self, "status", None)),
            "progress": self.get_progress_summary(),
            "working_directory": getattr(self, "working_directory", None),
        }


class ProjectFeature(ResourceRecord):
    """Feature DTO backed by one workspace resource record."""

    def __init__(self, values: Optional[dict[str, Any]] = None) -> None:
        super().__init__("ProjectFeature", values)

    def to_dict(self) -> dict[str, Any]:
        """Export the feature for agent context."""
        return {
            "id": getattr(self, "id", None),
            "name": getattr(self, "name", None),
            "description": getattr(self, "description", None),
            "category": _enum_value(getattr(self, "category", None)),
            "status": _enum_value(getattr(self, "status", None)),
            "priority": getattr(self, "priority", None),
            "verification_steps": getattr(self, "verification_steps", []) or [],
            "attempts": getattr(self, "attempts", None),
            "last_error": getattr(self, "last_error", None),
        }


class ProgressEntry(ResourceRecord):
    """Progress log DTO backed by one workspace resource record."""

    def __init__(self, values: Optional[dict[str, Any]] = None) -> None:
        super().__init__("ProgressEntry", values)

    def to_log_string(self) -> str:
        """Format the entry for human-readable logs."""
        timestamp = _timestamp(getattr(self, "timestamp", None))
        timestamp_str = (
            timestamp.strftime("%Y-%m-%d %H:%M:%S")
            if timestamp is not None
            else "unknown"
        )
        commit_hash = getattr(self, "git_commit_hash", None)
        commit = f" [{commit_hash[:7]}]" if commit_hash else ""
        files = getattr(self, "files_changed", None) or []
        files_str = f"\n  Files: {', '.join(files)}" if files else ""
        return (
            f"[{timestamp_str}]{commit} {getattr(self, 'action', '')}\n"
            f"  Outcome: {getattr(self, 'outcome', '')}{files_str}"
        )


class SessionState(ResourceRecord):
    """Session DTO backed by one workspace resource record."""

    def __init__(self, values: Optional[dict[str, Any]] = None) -> None:
        super().__init__("SessionState", values)

    def get_context_for_next_session(self) -> dict[str, Any]:
        """Get context to seed the next session."""
        return {
            "previous_session_id": getattr(self, "id", None),
            "last_action": getattr(self, "last_action", None),
            "recommended_next": getattr(
                self,
                "next_recommended_action",
                None,
            ),
            "working_memory": getattr(self, "working_memory", {}) or {},
            "error_to_fix": getattr(self, "error_state", None),
        }


class DecisionMemory(ResourceRecord):
    """Decision-memory DTO backed by one workspace resource record."""

    def __init__(self, values: Optional[dict[str, Any]] = None) -> None:
        super().__init__("DecisionMemory", values)

    def to_context_string(self) -> str:
        """Format the decision for agent context."""
        outcome = _enum_value(getattr(self, "outcome", None)) or "pending"
        score = float(getattr(self, "outcome_score", 0.0) or 0.0)
        return (
            f"Decision: {getattr(self, 'decision_made', '')}\n"
            f"Context: {getattr(self, 'decision_context', '')}\n"
            f"Outcome: {outcome} (score: {score:.2f})\n"
            "Lesson: "
            f"{getattr(self, 'lesson_learned', None) or 'None recorded'}"
        )


_RESOURCE_TYPES = {
    "ProjectState": ProjectState,
    "ProjectFeature": ProjectFeature,
    "ProgressEntry": ProgressEntry,
    "SessionState": SessionState,
    "DecisionMemory": DecisionMemory,
}


def _store(store: Optional[GuiResourceStore] = None) -> GuiResourceStore:
    """Return the shared resource store when one was not provided."""
    return store or get_resource_store()


def _wrap(resource_name: str, record: Any) -> Any:
    """Wrap a resource-store record in its local DTO class."""
    if record is None:
        return None
    wrapper_cls = _RESOURCE_TYPES.get(resource_name, ResourceRecord)
    if isinstance(record, wrapper_cls):
        return record
    if isinstance(record, ResourceRecord):
        values = ResourceRecord.to_dict(record)
    else:
        values = dict(record)
    return wrapper_cls(values)


def get_workspace_record(
    resource_name: str,
    record_id: Optional[int],
    *,
    store: Optional[GuiResourceStore] = None,
) -> Any:
    """Return one workspace record by primary key."""
    record = _store(store).get(resource_name, record_id)
    return _wrap(resource_name, record)


def first_workspace_record(
    resource_name: str,
    *,
    filters: Optional[dict[str, Any]] = None,
    store: Optional[GuiResourceStore] = None,
) -> Any:
    """Return the first matching workspace record."""
    record = _store(store).first(resource_name, filters=filters)
    return _wrap(resource_name, record)


def query_workspace_records(
    resource_name: str,
    *,
    filters: Optional[dict[str, Any]] = None,
    store: Optional[GuiResourceStore] = None,
) -> list[Any]:
    """Query workspace records and wrap them as local DTOs."""
    records = _store(store).query(resource_name, filters=filters)
    return [_wrap(resource_name, record) for record in records]


def create_workspace_record(
    resource_name: str,
    values: dict[str, Any],
    *,
    store: Optional[GuiResourceStore] = None,
) -> Any:
    """Create one workspace record and wrap it as a local DTO."""
    record = _store(store).create(resource_name, values)
    return _wrap(resource_name, record)


def update_workspace_record(
    resource_name: str,
    record_id: Optional[int],
    values: dict[str, Any],
    *,
    store: Optional[GuiResourceStore] = None,
) -> Any:
    """Update one workspace record and wrap the response."""
    record = _store(store).update(resource_name, record_id, values)
    return _wrap(resource_name, record)


def delete_workspace_record(
    resource_name: str,
    record_id: Optional[int],
    *,
    store: Optional[GuiResourceStore] = None,
) -> bool:
    """Delete one workspace record by primary key."""
    return _store(store).delete(resource_name, record_id)


__all__ = [
    "DecisionMemory",
    "DecisionOutcome",
    "FeatureCategory",
    "FeatureStatus",
    "ProgressEntry",
    "ProjectFeature",
    "ProjectState",
    "ProjectStatus",
    "SessionState",
    "create_workspace_record",
    "delete_workspace_record",
    "first_workspace_record",
    "get_workspace_record",
    "query_workspace_records",
    "update_workspace_record",
]
