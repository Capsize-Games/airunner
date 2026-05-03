"""Result types for AIRunner coding-project open flows."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from airunner.components.document_editor.project.airunner_project_settings import (
    AirunnerProjectSettings,
)
from airunner.components.document_editor.project.airunner_workspace_config import (
    AirunnerWorkspaceConfig,
)

if TYPE_CHECKING:
    from airunner.components.document_editor.project.airunner_project_service import (
        AirunnerProjectService,
    )


@dataclass(frozen=True)
class AirunnerProjectOpenResult:
    """Outcome for project initialization or open flows."""

    project_path: str
    service: "AirunnerProjectService | None" = None
    workspace: AirunnerWorkspaceConfig | None = None
    settings: AirunnerProjectSettings | None = None
    errors: list[str] = field(default_factory=list)
    recovery_suggestions: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return whether the project opened successfully."""
        return (
            self.workspace is not None
            and self.settings is not None
            and not self.errors
        )

    @property
    def requires_recovery(self) -> bool:
        """Return whether the project needs explicit recovery work."""
        return bool(self.errors)