"""Trust and autonomy settings for AIRunner coding projects."""

from dataclasses import dataclass

from airunner.components.document_editor.project.airunner_autonomy_mode import (
    AirunnerAutonomyMode,
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
        )

    def to_dict(self) -> dict:
        """Serialize project settings to a dictionary."""
        return {
            "schema_version": self.schema_version,
            "trust_level": self.trust_level.value,
            "autonomy_mode": self.autonomy_mode.value,
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
        if self._requires_trusted_project():
            return [
                "Untrusted projects must use review-first autonomy mode."
            ]
        return []

    def _requires_trusted_project(self) -> bool:
        """Check whether the selected autonomy mode requires trust."""
        trusted = self.trust_level == AirunnerTrustLevel.TRUSTED
        review_first = self.autonomy_mode == AirunnerAutonomyMode.REVIEW_FIRST
        return not trusted and not review_first