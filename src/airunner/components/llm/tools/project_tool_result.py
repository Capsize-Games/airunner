"""Structured results for project-aware agent tool operations."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProjectToolResult:
    """Represent one project-aware tool operation result."""

    operation: str
    success: bool
    message: str
    root_name: str | None = None
    rel_path: str | None = None
    abs_path: str | None = None
    content: str | None = None
    files: list[dict[str, str]] = field(default_factory=list)
    matches: list[dict[str, Any]] = field(default_factory=list)
    audit_record_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the tool result to a JSON-compatible mapping."""
        return {
            "operation": self.operation,
            "success": self.success,
            "message": self.message,
            "root_name": self.root_name,
            "rel_path": self.rel_path,
            "abs_path": self.abs_path,
            "content": self.content,
            "files": list(self.files),
            "matches": list(self.matches),
            "audit_record_id": self.audit_record_id,
            "error": self.error,
        }