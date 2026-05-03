"""Project service for AIRunner coding workspaces."""

import json
import os
import re

from airunner.components.document_editor.project.airunner_project_root import (
    AirunnerProjectRoot,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    SETTINGS_FILE,
    WORKSPACE_FILE,
    required_project_directories,
)
from airunner.components.document_editor.project.airunner_project_settings import (
    AirunnerProjectSettings,
)
from airunner.components.document_editor.project.airunner_workspace_config import (
    AirunnerWorkspaceConfig,
)
from airunner.components.document_editor.workspace_manager import (
    WorkspaceManager,
)


class AirunnerProjectService:
    """Manage .airunner state and multi-root project workspaces."""

    def __init__(self, project_path: str):
        """Initialize the project service for a workspace directory."""
        self.project_path = os.path.expanduser(os.path.abspath(project_path))
        self.workspace_manager = WorkspaceManager(self.project_path)
        self._root_managers: dict[str, WorkspaceManager] = {}

    def exists(self) -> bool:
        """Return whether the .airunner metadata exists on disk."""
        return self.workspace_manager.exists(WORKSPACE_FILE) and \
            self.workspace_manager.exists(SETTINGS_FILE)

    def initialize(
        self,
        project_name: str | None = None,
        additional_roots: list[str] | None = None,
        settings: AirunnerProjectSettings | None = None,
    ) -> tuple[AirunnerWorkspaceConfig, AirunnerProjectSettings]:
        """Initialize a new .airunner workspace and return its config."""
        roots = self._build_roots(additional_roots or [])
        workspace = AirunnerWorkspaceConfig.create_default(
            project_name=project_name or self._default_project_name(),
            roots=roots,
        )
        project_settings = settings or AirunnerProjectSettings()
        self._validate_or_raise(workspace, project_settings)
        self._ensure_layout(workspace)
        self.save_workspace(workspace)
        self.save_settings(project_settings)
        return self.load_workspace(), self.load_settings()

    def load_workspace(self) -> AirunnerWorkspaceConfig:
        """Load and deserialize workspace metadata."""
        payload = self._read_json(WORKSPACE_FILE)
        return AirunnerWorkspaceConfig.from_dict(payload)

    def load_settings(self) -> AirunnerProjectSettings:
        """Load and deserialize project settings metadata."""
        payload = self._read_json(SETTINGS_FILE)
        return AirunnerProjectSettings.from_dict(payload)

    def save_workspace(self, workspace: AirunnerWorkspaceConfig) -> None:
        """Persist workspace metadata to .airunner/workspace.json."""
        refreshed = workspace.with_updated_timestamp()
        self._write_json(WORKSPACE_FILE, refreshed.to_dict())
        self._root_managers.clear()

    def save_settings(self, settings: AirunnerProjectSettings) -> None:
        """Persist project settings to .airunner/settings.json."""
        self._write_json(SETTINGS_FILE, settings.to_dict())

    def list_roots(self) -> list[AirunnerProjectRoot]:
        """Return the configured workspace roots for the project."""
        return self.load_workspace().roots

    def resolve_root_path(self, root_name: str) -> str:
        """Resolve a configured root name to an absolute filesystem path."""
        root = self._root_by_name(root_name)
        return self._resolve_stored_path(root.path)

    def get_workspace_manager(
        self,
        root_name: str | None = None,
    ) -> WorkspaceManager:
        """Return a WorkspaceManager scoped to a configured root."""
        name = root_name or self.load_workspace().primary_root
        if name not in self._root_managers:
            self._root_managers[name] = WorkspaceManager(
                self.resolve_root_path(name)
            )
        return self._root_managers[name]

    def resolve_path(
        self,
        rel_path: str,
        root_name: str | None = None,
    ) -> str:
        """Resolve a root-relative path to an absolute path."""
        root_path = self.resolve_root_path(
            root_name or self.load_workspace().primary_root
        )
        abs_path = os.path.normpath(os.path.join(root_path, rel_path))
        if not self._is_within(abs_path, root_path):
            raise ValueError(
                f"Path '{rel_path}' is outside project root '{root_path}'."
            )
        return abs_path

    def project_relative_path(
        self,
        candidate_path: str,
    ) -> tuple[str, str] | None:
        """Return the owning root name and relative path for a file."""
        root = self.root_for_path(candidate_path)
        if root is None:
            return None
        abs_path = os.path.expanduser(os.path.abspath(candidate_path))
        root_path = self.resolve_root_path(root.name)
        rel_path = os.path.relpath(abs_path, root_path)
        return root.name, os.path.normpath(rel_path)

    def read_file(
        self,
        rel_path: str,
        root_name: str | None = None,
    ) -> str:
        """Read a file through the configured project root."""
        return self.get_workspace_manager(root_name).read_file(rel_path)

    def write_file(
        self,
        rel_path: str,
        content: str,
        root_name: str | None = None,
        *,
        backup: bool = True,
        create_dirs: bool = True,
    ) -> str:
        """Write a file through the configured project root."""
        return self.get_workspace_manager(root_name).write_file(
            rel_path,
            content,
            backup=backup,
            create_dirs=create_dirs,
        )

    def apply_patch(
        self,
        rel_path: str,
        patch_content: str,
        root_name: str | None = None,
    ) -> str:
        """Apply a patch through the configured project root."""
        return self.get_workspace_manager(root_name).apply_patch(
            rel_path,
            patch_content,
        )

    def list_files(
        self,
        rel_dir: str = "",
        root_name: str | None = None,
        *,
        pattern: str = "*.py",
        recursive: bool = False,
    ) -> list[str]:
        """List files from a configured project root."""
        return self.get_workspace_manager(root_name).list_files(
            rel_dir,
            pattern=pattern,
            recursive=recursive,
        )

    def contains_path(self, candidate_path: str) -> bool:
        """Return whether a path belongs to any configured workspace root."""
        return self.root_for_path(candidate_path) is not None

    def root_for_path(
        self,
        candidate_path: str,
    ) -> AirunnerProjectRoot | None:
        """Return the root owning a path, if any."""
        path = os.path.expanduser(os.path.abspath(candidate_path))
        roots = sorted(self.list_roots(), key=self._root_sort_key, reverse=True)
        for root in roots:
            if self._is_within(path, self._resolve_stored_path(root.path)):
                return root
        return None

    def validate(self) -> list[str]:
        """Return validation errors for persisted project state."""
        if not self.exists():
            return ["The .airunner metadata has not been initialized."]
        workspace = self.load_workspace()
        settings = self.load_settings()
        errors = workspace.validate() + settings.validate()
        errors.extend(self._missing_root_errors(workspace))
        return errors

    def _default_project_name(self) -> str:
        """Return the default project name based on the project path."""
        return os.path.basename(self.project_path.rstrip(os.sep)) or "AIRunner"

    def _build_roots(self, additional_roots: list[str]) -> list[AirunnerProjectRoot]:
        """Build the configured workspace roots for initialization."""
        roots = [AirunnerProjectRoot(name="workspace", path=".")]
        names = {"workspace"}
        paths = {"."}
        for path in additional_roots:
            stored_path = self._stored_root_path(path)
            if stored_path in paths:
                continue
            root_name = self._unique_root_name(path, names)
            roots.append(AirunnerProjectRoot(name=root_name, path=stored_path))
            names.add(root_name)
            paths.add(stored_path)
        return roots

    def _unique_root_name(self, path: str, names: set[str]) -> str:
        """Create a stable unique root name for an additional root path."""
        resolved = self._resolve_stored_path(path)
        base_name = os.path.basename(resolved) or "root"
        candidate = re.sub(r"[^a-zA-Z0-9._-]+", "-", base_name).strip("-")
        candidate = candidate or "root"
        index = 2
        while candidate in names:
            candidate = f"{candidate}-{index}"
            index += 1
        return candidate

    def _stored_root_path(self, path: str) -> str:
        """Return the stored root path for a configured workspace root."""
        resolved = self._resolve_stored_path(path)
        if self._is_within(resolved, self.project_path):
            relative = os.path.relpath(resolved, self.project_path)
            return os.path.normpath(relative)
        return resolved

    def _resolve_stored_path(self, path: str) -> str:
        """Resolve a stored root path to an absolute path."""
        if os.path.isabs(path):
            return os.path.normpath(path)
        joined = os.path.join(self.project_path, path)
        return os.path.normpath(joined)

    def _validate_or_raise(
        self,
        workspace: AirunnerWorkspaceConfig,
        settings: AirunnerProjectSettings,
    ) -> None:
        """Raise a ValueError if the pending project config is invalid."""
        errors = workspace.validate() + settings.validate()
        if errors:
            raise ValueError("\n".join(errors))

    def _ensure_layout(self, workspace: AirunnerWorkspaceConfig) -> None:
        """Create the required project layout on disk."""
        os.makedirs(self.project_path, exist_ok=True)
        for path in required_project_directories():
            os.makedirs(os.path.join(self.project_path, path), exist_ok=True)
        for root in workspace.roots:
            os.makedirs(self._resolve_stored_path(root.path), exist_ok=True)

    def _read_json(self, rel_path: str) -> dict:
        """Read a JSON file relative to the project root."""
        return json.loads(self.workspace_manager.read_file(rel_path))

    def _write_json(self, rel_path: str, payload: dict) -> None:
        """Write a JSON file relative to the project root."""
        content = json.dumps(payload, indent=2, sort_keys=True)
        self.workspace_manager.write_file(
            rel_path,
            content + "\n",
            backup=True,
        )

    def _root_by_name(self, root_name: str) -> AirunnerProjectRoot:
        """Return a configured root by name or raise a ValueError."""
        for root in self.list_roots():
            if root.name == root_name:
                return root
        raise ValueError(f"Unknown project root: {root_name}")

    def _missing_root_errors(
        self,
        workspace: AirunnerWorkspaceConfig,
    ) -> list[str]:
        """Return validation errors for missing root directories."""
        errors: list[str] = []
        for root in workspace.roots:
            if os.path.exists(self._resolve_stored_path(root.path)):
                continue
            errors.append(f"Missing workspace root: {root.name}")
        return errors

    def _root_sort_key(self, root: AirunnerProjectRoot) -> int:
        """Return the sort key used to prefer deeper root matches."""
        return len(self._resolve_stored_path(root.path))

    def _is_within(self, candidate: str, parent: str) -> bool:
        """Return whether a path is located within a parent directory."""
        try:
            common = os.path.commonpath([candidate, parent])
        except ValueError:
            return False
        return common == os.path.normpath(parent)