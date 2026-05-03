"""Persisted Python environment metadata for coding projects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AirunnerPythonEnvironmentSelection:
    """Describe the selected Python environment for one coding project."""

    manager: str
    interpreter_path: str | None = None
    environment_path: str | None = None
    python_version: str | None = None
    activate_command: str | None = None

    @classmethod
    def from_dict(
        cls,
        data: dict | None,
    ) -> "AirunnerPythonEnvironmentSelection | None":
        """Deserialize Python environment metadata from a dictionary."""
        if not data:
            return None
        return cls(
            manager=str(data.get("manager", "")),
            interpreter_path=data.get("interpreter_path"),
            environment_path=data.get("environment_path"),
            python_version=data.get("python_version"),
            activate_command=data.get("activate_command"),
        )

    def to_dict(self) -> dict[str, str | None]:
        """Serialize Python environment metadata to a dictionary."""
        return {
            "manager": self.manager,
            "interpreter_path": self.interpreter_path,
            "environment_path": self.environment_path,
            "python_version": self.python_version,
            "activate_command": self.activate_command,
        }

    def validate(self) -> list[str]:
        """Return validation errors for the environment selection."""
        if self.manager.strip():
            return []
        return ["Python environment manager must not be empty."]