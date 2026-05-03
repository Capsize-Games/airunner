"""Trust, autonomy, and Python bootstrap settings for coding projects."""

from dataclasses import dataclass, replace

from airunner.components.document_editor.project.airunner_autonomy_mode import (
    AirunnerAutonomyMode,
)
from airunner.components.document_editor.project.airunner_python_environment_selection import (
    AirunnerPythonEnvironmentSelection,
)
from airunner.components.document_editor.project.airunner_trust_level import (
    AirunnerTrustLevel,
)


@dataclass(frozen=True)
class AirunnerProjectSettings:
    """Serialized trust and autonomy settings for a project."""

    schema_version: int = 1
    trust_level: AirunnerTrustLevel = AirunnerTrustLevel.UNTRUSTED
    autonomy_mode: AirunnerAutonomyMode = (
        AirunnerAutonomyMode.REVIEW_FIRST
    )
    bootstrap_profile: str | None = None
    python_environment: AirunnerPythonEnvironmentSelection | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "AirunnerProjectSettings":
        """Deserialize project settings from a dictionary."""
        trust_level = data.get(
            "trust_level",
            AirunnerTrustLevel.UNTRUSTED.value,
        )
        autonomy_mode = data.get(
            "autonomy_mode",
            AirunnerAutonomyMode.REVIEW_FIRST.value,
        )
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            trust_level=AirunnerTrustLevel(str(trust_level)),
            autonomy_mode=AirunnerAutonomyMode(str(autonomy_mode)),
            bootstrap_profile=data.get("bootstrap_profile"),
            python_environment=AirunnerPythonEnvironmentSelection.from_dict(
                data.get("python_environment")
            ),
        )

    def to_dict(self) -> dict:
        """Serialize project settings to a dictionary."""
        return {
            "schema_version": self.schema_version,
            "trust_level": self.trust_level.value,
            "autonomy_mode": self.autonomy_mode.value,
            "bootstrap_profile": self.bootstrap_profile,
            "python_environment": None
            if self.python_environment is None
            else self.python_environment.to_dict(),
        }

    def effective_policy(self) -> dict[str, bool]:
        """Return the effective policy flags for the current settings."""
        if self.autonomy_mode == AirunnerAutonomyMode.REVIEW_FIRST:
            return {
                "require_command_approval": True,
                "require_file_review": True,
                "allow_background_agents": False,
            }
        if self.autonomy_mode == AirunnerAutonomyMode.MIXED:
            return {
                "require_command_approval": False,
                "require_file_review": True,
                "allow_background_agents": True,
            }
        return {
            "require_command_approval": False,
            "require_file_review": False,
            "allow_background_agents": True,
        }

    def validate(self) -> list[str]:
        """Return validation errors for the trust and autonomy settings."""
        if self.bootstrap_profile not in {None, "python-package"}:
            return [
                "Unsupported bootstrap_profile in project settings."
            ]
        if self.python_environment is not None:
            errors = self.python_environment.validate()
            if errors:
                return errors
        if self._requires_trusted_project():
            return [
                "Untrusted projects must use review-first autonomy mode."
            ]
        return []

    def with_bootstrap_profile(
        self,
        bootstrap_profile: str,
    ) -> "AirunnerProjectSettings":
        """Return settings with an updated bootstrap profile."""
        return replace(self, bootstrap_profile=bootstrap_profile)

    def with_python_environment(
        self,
        python_environment: AirunnerPythonEnvironmentSelection,
    ) -> "AirunnerProjectSettings":
        """Return settings with updated Python environment metadata."""
        return replace(self, python_environment=python_environment)

    def _requires_trusted_project(self) -> bool:
        """Check whether the selected autonomy mode requires trust."""
        trusted = self.trust_level == AirunnerTrustLevel.TRUSTED
        review_first = self.autonomy_mode == AirunnerAutonomyMode.REVIEW_FIRST
        return not trusted and not review_first