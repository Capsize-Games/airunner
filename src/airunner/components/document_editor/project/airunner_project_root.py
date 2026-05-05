"""Workspace root definitions for AIRunner coding projects."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AirunnerProjectRoot:
    """A single workspace root in an AIRunner coding project."""

    name: str
    path: str

    def normalized_path(self) -> str:
        """Return the normalized stored path for the workspace root."""
        return os.path.normpath(self.path or ".")

    def to_dict(self) -> dict[str, str]:
        """Serialize the workspace root to a dictionary."""
        return {"name": self.name, "path": self.normalized_path()}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "AirunnerProjectRoot":
        """Build a workspace root from serialized data."""
        name = (data.get("name") or "").strip()
        path = (data.get("path") or ".").strip()
        if not name:
            raise ValueError("Project roots must include a name.")
        return cls(name=name, path=path)