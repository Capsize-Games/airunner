"""Entry points for AIRunner coding-project create and open flows."""

from datetime import datetime, timezone
import json
import os

from airunner.components.document_editor.project.airunner_project_open_result import (
    AirunnerProjectOpenResult,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    PROJECT_DIR_NAME,
)
from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project.airunner_project_settings import (
    AirunnerProjectSettings,
)
from airunner.components.document_editor.project.airunner_recent_project_entry import (
    AirunnerRecentProjectEntry,
)
from airunner.settings import AIRUNNER_RECENT_CODING_WORKSPACES_PATH


def _utc_now_iso() -> str:
    """Return an ISO8601 UTC timestamp for recent-project metadata."""
    return datetime.now(timezone.utc).isoformat()


class AirunnerProjectManager:
    """Manage supported coding-project entry flows and recent workspaces."""

    def __init__(self, recent_projects_path: str | None = None):
        """Initialize the manager with an optional recent-project store."""
        store_path = (
            recent_projects_path or AIRUNNER_RECENT_CODING_WORKSPACES_PATH
        )
        self.recent_projects_path = os.path.expanduser(
            os.path.abspath(store_path)
        )

    def create_project(
        self,
        project_path: str,
        project_name: str | None = None,
        additional_roots: list[str] | None = None,
        settings: AirunnerProjectSettings | None = None,
    ) -> AirunnerProjectOpenResult:
        """Create a coding project and record it in recent workspaces."""
        service = AirunnerProjectService(project_path)
        if service.exists():
            return self.open_project(project_path)
        workspace, _ = service.initialize(
            project_name=project_name,
            additional_roots=additional_roots,
            settings=settings,
        )
        return self._success_result(service, workspace.project_name)

    def open_project(self, project_path: str) -> AirunnerProjectOpenResult:
        """Open an existing coding project or return recovery guidance."""
        service = AirunnerProjectService(project_path)
        if not service.exists():
            return self._missing_metadata_result(service.project_path)
        try:
            errors = service.validate()
            if errors:
                return self._error_result(
                    service.project_path,
                    errors,
                    [self._repair_message()],
                )
            workspace = service.load_workspace()
            service.load_settings()
        except json.JSONDecodeError:
            return self._error_result(
                service.project_path,
                ["The .airunner metadata is not valid JSON."],
                [self._repair_message()],
            )
        except FileNotFoundError:
            return self._error_result(
                service.project_path,
                ["The .airunner metadata is incomplete."],
                [self._repair_message()],
            )
        return self._success_result(service, workspace.project_name)

    def list_recent_projects(self) -> list[AirunnerRecentProjectEntry]:
        """Return persisted recent coding-project entries."""
        if not os.path.exists(self.recent_projects_path):
            return []
        try:
            with open(self.recent_projects_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return []
        return [
            AirunnerRecentProjectEntry.from_dict(item)
            for item in payload.get("projects", [])
        ]

    def _success_result(
        self,
        service: AirunnerProjectService,
        project_name: str,
    ) -> AirunnerProjectOpenResult:
        """Build a successful project-open result and update recents."""
        self._remember_project(service.project_path, project_name)
        return AirunnerProjectOpenResult(
            project_path=service.project_path,
            service=service,
            workspace=service.load_workspace(),
            settings=service.load_settings(),
        )

    def _missing_metadata_result(
        self,
        project_path: str,
    ) -> AirunnerProjectOpenResult:
        """Return recovery instructions for missing or partial metadata."""
        project_dir = os.path.join(project_path, PROJECT_DIR_NAME)
        if os.path.isdir(project_dir):
            return self._error_result(
                project_path,
                ["The .airunner metadata is incomplete."],
                [self._repair_message()],
            )
        return self._error_result(
            project_path,
            ["This folder is not an AIRunner coding project yet."],
            [
                "Initialize the project to create the .airunner contract "
                "before opening it as a coding workspace."
            ],
        )

    def _remember_project(self, project_path: str, project_name: str) -> None:
        """Persist a project in the recent-workspace list."""
        normalized_path = os.path.expanduser(os.path.abspath(project_path))
        recent_projects = [
            entry
            for entry in self.list_recent_projects()
            if entry.path != normalized_path
        ]
        recent_projects.insert(
            0,
            AirunnerRecentProjectEntry(
                path=normalized_path,
                project_name=project_name,
                last_opened_at=_utc_now_iso(),
            ),
        )
        payload = {
            "projects": [entry.to_dict() for entry in recent_projects[:20]]
        }
        directory = os.path.dirname(self.recent_projects_path)
        os.makedirs(directory, exist_ok=True)
        with open(self.recent_projects_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def _error_result(
        self,
        project_path: str,
        errors: list[str],
        recovery_suggestions: list[str],
    ) -> AirunnerProjectOpenResult:
        """Build a failed project-open result."""
        return AirunnerProjectOpenResult(
            project_path=project_path,
            errors=errors,
            recovery_suggestions=recovery_suggestions,
        )

    def _repair_message(self) -> str:
        """Return the standard recovery guidance for broken metadata."""
        return (
            "Repair or recreate the missing .airunner metadata before "
            "opening this coding workspace."
        )