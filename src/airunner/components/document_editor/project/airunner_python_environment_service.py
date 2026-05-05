"""Ensure local Python environments exist for coding projects."""

from contextlib import nullcontext
import ensurepip
import os
import shutil
import sys
import venv

from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project.airunner_python_environment_selection import (
    AirunnerPythonEnvironmentSelection,
)
from airunner.vendor.facehuggershield.darklock import os as darklock_os


class AirunnerPythonEnvironmentService:
    """Provision and persist Python environments for one project."""

    def __init__(self, project_service: AirunnerProjectService):
        self.project_service = project_service

    def ensure_environment(self) -> AirunnerPythonEnvironmentSelection | None:
        """Create and persist the selected Python environment if needed."""
        settings = self.project_service.load_settings()
        selection = self._selected_environment(
            settings.bootstrap_profile,
            settings.python_environment,
        )
        if selection is None:
            return None
        self._persist_selection(settings.python_environment, selection, settings)
        if not selection.is_ready():
            self._ensure_ready_environment(selection)
        return selection

    def _ensure_ready_environment(
        self,
        selection: AirunnerPythonEnvironmentSelection,
    ) -> None:
        """Create or rebuild a selected environment until it is ready."""
        if selection.manager != "venv":
            self._create_environment(selection)
            return
        self._rebuild_environment(selection)

    def _selected_environment(
        self,
        bootstrap_profile: str | None,
        selection: AirunnerPythonEnvironmentSelection | None,
    ) -> AirunnerPythonEnvironmentSelection | None:
        """Return the active selection or the default local venv."""
        if selection is not None:
            return selection
        if bootstrap_profile != "python-package":
            return None
        return AirunnerPythonEnvironmentSelection.for_local_venv(
            self.project_service.project_path
        )

    def _persist_selection(
        self,
        current: AirunnerPythonEnvironmentSelection | None,
        selection: AirunnerPythonEnvironmentSelection,
        settings,
    ) -> None:
        """Save a default selection when project settings do not have one."""
        if current == selection:
            return
        self.project_service.save_settings(
            settings.with_python_environment(selection)
        )

    def _create_environment(
        self,
        selection: AirunnerPythonEnvironmentSelection,
    ) -> None:
        """Create a local virtual environment for the project."""
        env_path = selection.resolved_environment_path()
        if selection.manager != "venv" or not env_path:
            return
        builder = self._env_builder()
        with self._creation_override([env_path]):
            builder.create(env_path)

    def _rebuild_environment(
        self,
        selection: AirunnerPythonEnvironmentSelection,
    ) -> None:
        """Remove an incomplete local venv before recreating it."""
        env_path = selection.resolved_environment_path()
        if not env_path:
            return
        with self._creation_override([env_path]):
            if os.path.isdir(env_path):
                shutil.rmtree(env_path)
            elif os.path.exists(env_path):
                os.remove(env_path)
            self._env_builder().create(env_path)

    def _env_builder(self) -> venv.EnvBuilder:
        """Return the venv builder used for project-local environments."""
        return venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt")

    def _creation_override(self, extra_paths: list[str] | None = None):
        """Temporarily allow interpreter reads during venv creation."""
        paths = set(self._creation_allowed_paths())
        for path in extra_paths or []:
            if path:
                paths.add(path)
        if not paths:
            return nullcontext()
        return darklock_os.user_override(paths=sorted(paths))

    def _creation_allowed_paths(self) -> list[str]:
        """Return interpreter paths venv may need to inspect."""
        paths = {sys.executable}
        base_executable = getattr(sys, "_base_executable", None)
        if base_executable:
            paths.add(base_executable)
        for module in (venv, ensurepip):
            module_path = getattr(module, "__file__", None)
            if module_path:
                paths.add(os.path.dirname(os.path.abspath(module_path)))
        return sorted(path for path in paths if path)