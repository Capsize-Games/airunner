"""Workspace metadata for AIRunner coding projects."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4

from airunner.components.document_editor.project.airunner_project_root import (
    AirunnerProjectRoot,
)


def _utc_now_iso() -> str:
    """Return an ISO8601 UTC timestamp for project metadata."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AirunnerWorkspaceConfig:
    """Serialized workspace metadata for an AIRunner coding project."""

    schema_version: int
    project_id: str
    project_name: str
    primary_root: str
    roots: list[AirunnerProjectRoot]
    created_at: str
    updated_at: str

    @classmethod
    def create_default(
        cls,
        project_name: str,
        roots: list[AirunnerProjectRoot],
    ) -> "AirunnerWorkspaceConfig":
        """Create a default workspace config for a new project."""
        timestamp = _utc_now_iso()
        return cls(
            schema_version=1,
            project_id=str(uuid4()),
            project_name=project_name,
            primary_root=roots[0].name,
            roots=roots,
            created_at=timestamp,
            updated_at=timestamp,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "AirunnerWorkspaceConfig":
        """Deserialize workspace metadata from a dictionary."""
        roots = [
            AirunnerProjectRoot.from_dict(item)
            for item in data.get("roots", [])
        ]
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            project_id=str(data.get("project_id", "")),
            project_name=str(data.get("project_name", "")),
            primary_root=str(data.get("primary_root", "workspace")),
            roots=roots,
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )

    def to_dict(self) -> dict:
        """Serialize workspace metadata to a dictionary."""
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "primary_root": self.primary_root,
            "roots": [root.to_dict() for root in self.roots],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def validate(self) -> list[str]:
        """Return validation errors for the workspace metadata."""
        errors: list[str] = []
        if not self.project_name.strip():
            errors.append("Workspace config requires a project_name.")
        if not self.roots:
            errors.append("Workspace config requires at least one root.")
        errors.extend(self._validate_root_names())
        errors.extend(self._validate_root_paths())
        if self.primary_root not in {root.name for root in self.roots}:
            errors.append("Workspace config primary_root must match a root.")
        return errors

    def with_updated_timestamp(self) -> "AirunnerWorkspaceConfig":
        """Return a copy with a refreshed updated_at timestamp."""
        return replace(self, updated_at=_utc_now_iso())

    def _validate_root_names(self) -> list[str]:
        """Validate workspace root names."""
        names = [root.name for root in self.roots]
        if len(names) == len(set(names)):
            return []
        return ["Workspace roots must use unique names."]

    def _validate_root_paths(self) -> list[str]:
        """Validate workspace root paths."""
        paths = [root.normalized_path() for root in self.roots]
        if len(paths) == len(set(paths)):
            return []
        return ["Workspace roots must use unique paths."]