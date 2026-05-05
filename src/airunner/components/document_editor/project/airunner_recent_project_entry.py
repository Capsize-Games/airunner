"""Recent coding-project metadata for AIRunner workspaces."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AirunnerRecentProjectEntry:
    """A recently opened AIRunner coding project."""

    path: str
    project_name: str
    last_opened_at: str

    @classmethod
    def from_dict(cls, data: dict) -> "AirunnerRecentProjectEntry":
        """Deserialize a recent-project entry from a dictionary."""
        return cls(
            path=str(data.get("path", "")),
            project_name=str(data.get("project_name", "")),
            last_opened_at=str(data.get("last_opened_at", "")),
        )

    def to_dict(self) -> dict[str, str]:
        """Serialize a recent-project entry to a dictionary."""
        return {
            "path": self.path,
            "project_name": self.project_name,
            "last_opened_at": self.last_opened_at,
        }