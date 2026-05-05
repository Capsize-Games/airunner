"""Persisted Python environment metadata for coding projects."""

from dataclasses import dataclass
import os
import sys


@dataclass(frozen=True)
class AirunnerPythonEnvironmentSelection:
    """Describe the selected Python environment for one coding project."""

    manager: str
    interpreter_path: str | None = None
    environment_path: str | None = None
    python_version: str | None = None
    activate_command: str | None = None

    @classmethod
    def for_local_venv(
        cls,
        project_path: str,
    ) -> "AirunnerPythonEnvironmentSelection":
        """Return the default local .venv selection for one project."""
        env_path = os.path.abspath(os.path.join(project_path, ".venv"))
        scripts_dir = "Scripts" if os.name == "nt" else "bin"
        python_name = "python.exe" if os.name == "nt" else "python"
        activate_name = "activate.bat" if os.name == "nt" else "activate"
        activate_path = os.path.join(env_path, scripts_dir, activate_name)
        activate_command = f'call "{activate_path}"'
        if os.name != "nt":
            activate_command = f"source {activate_path}"
        version = f"{sys.version_info.major}.{sys.version_info.minor}"
        return cls(
            manager="venv",
            interpreter_path=os.path.join(env_path, scripts_dir, python_name),
            environment_path=env_path,
            python_version=version,
            activate_command=activate_command,
        )

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

    def interpreter_exists(self) -> bool:
        """Return whether the selected interpreter exists on disk."""
        if not self.interpreter_path:
            return False
        return os.path.isfile(self.interpreter_path)

    def resolved_environment_path(self) -> str | None:
        """Return the environment directory for local venv selections."""
        if self.environment_path:
            return self.environment_path
        if not self.interpreter_path:
            return None
        scripts_dir = os.path.dirname(self.interpreter_path)
        return os.path.dirname(scripts_dir)

    def activate_script_exists(self) -> bool:
        """Return whether the environment activation script exists."""
        env_path = self.resolved_environment_path()
        if not env_path:
            return False
        scripts_dir = "Scripts" if os.name == "nt" else "bin"
        activate_name = "activate.bat" if os.name == "nt" else "activate"
        activate_path = os.path.join(env_path, scripts_dir, activate_name)
        return os.path.isfile(activate_path)

    def configuration_exists(self) -> bool:
        """Return whether the virtual environment metadata exists."""
        env_path = self.resolved_environment_path()
        if not env_path:
            return False
        return os.path.isfile(os.path.join(env_path, "pyvenv.cfg"))

    def is_ready(self) -> bool:
        """Return whether the selected environment is ready for use."""
        if self.manager != "venv":
            return self.interpreter_exists()
        return (
            self.interpreter_exists()
            and self.activate_script_exists()
            and self.configuration_exists()
        )

    def validate(self) -> list[str]:
        """Return validation errors for the environment selection."""
        if self.manager.strip():
            return []
        return ["Python environment manager must not be empty."]