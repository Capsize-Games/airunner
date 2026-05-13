"""Unit tests for AIRunner coding-project bootstrap flows."""

from contextlib import contextmanager
import os
from pathlib import Path

import airunner.components.document_editor.project.airunner_python_environment_service as python_environment_service_module

from airunner.components.document_editor.project import (
    AirunnerProjectManager,
    AirunnerProjectService,
    AirunnerProjectSettings,
)
from airunner.components.document_editor.project import (
    AirunnerPythonEnvironmentSelection,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    INSTRUCTIONS_FILE,
    PROMPT_TEMPLATES_DIR,
    PROJECT_DIR_NAME,
)
from airunner.components.document_editor.project.airunner_python_environment_service import (
    AirunnerPythonEnvironmentService,
)


def _fake_create_environment(self, selection):
    """Create a lightweight interpreter file for environment tests."""
    del self
    interpreter = Path(selection.interpreter_path)
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    activate = interpreter.parent / "activate"
    activate.write_text("source .venv/bin/activate\n", encoding="utf-8")
    env_path = Path(selection.resolved_environment_path())
    (env_path / "pyvenv.cfg").write_text("home = /usr/bin\n")


def test_project_manager_creates_project_and_tracks_recents(tmp_path):
    """Creating a project should persist it in recent workspaces."""
    recents_path = tmp_path / "recent_workspaces.json"
    project_path = tmp_path / "demo-project"
    manager = AirunnerProjectManager(str(recents_path))

    result = manager.create_project(
        str(project_path),
        project_name="Demo Project",
    )

    assert result.ok
    assert result.workspace is not None
    recent_projects = manager.list_recent_projects()
    assert len(recent_projects) == 1
    assert recent_projects[0].path == str(project_path)
    assert recent_projects[0].project_name == "Demo Project"


def test_project_manager_opens_existing_project(tmp_path):
    """Opening an existing project should load its metadata cleanly."""
    recents_path = tmp_path / "recent_workspaces.json"
    project_path = tmp_path / "demo-project"
    manager = AirunnerProjectManager(str(recents_path))
    manager.create_project(str(project_path), project_name="Demo Project")

    reopened = AirunnerProjectManager(str(recents_path)).open_project(
        str(project_path)
    )

    assert reopened.ok
    assert reopened.workspace is not None
    assert reopened.workspace.project_name == "Demo Project"
    assert reopened.settings is not None


def test_project_manager_flags_missing_metadata(tmp_path):
    """Opening a plain folder should return initialization guidance."""
    recents_path = tmp_path / "recent_workspaces.json"
    project_path = tmp_path / "plain-folder"
    project_path.mkdir()
    manager = AirunnerProjectManager(str(recents_path))

    result = manager.open_project(str(project_path))

    assert not result.ok
    assert result.requires_recovery
    assert result.errors == [
        "This folder is not an AIRunner coding project yet."
    ]
    assert result.recovery_suggestions


def test_project_manager_flags_partial_metadata(tmp_path):
    """Opening a partially initialized project should return recovery help."""
    recents_path = tmp_path / "recent_workspaces.json"
    project_path = tmp_path / "broken-project"
    manager = AirunnerProjectManager(str(recents_path))
    project_dir = project_path / PROJECT_DIR_NAME
    project_dir.mkdir(parents=True)
    (project_dir / "workspace.json").write_text("{}\n", encoding="utf-8")

    result = manager.open_project(str(project_path))

    assert not result.ok
    assert result.requires_recovery
    assert result.errors == ["The .airunner metadata is incomplete."]
    assert result.recovery_suggestions == [
        "Repair or recreate the missing .airunner metadata before opening "
        "this coding workspace."
    ]


def test_project_manager_creates_python_project_scaffold(
    tmp_path,
    monkeypatch,
):
    """Python project creation should scaffold a usable package layout."""
    monkeypatch.setattr(
        AirunnerPythonEnvironmentService,
        "_create_environment",
        _fake_create_environment,
    )
    recents_path = tmp_path / "recent_workspaces.json"
    project_path = tmp_path / "python-project"
    manager = AirunnerProjectManager(str(recents_path))

    result = manager.create_python_project(
        str(project_path),
        project_name="Python Project",
        package_name="python_project",
    )

    assert result.ok
    assert result.settings.bootstrap_profile == "python-package"
    assert result.settings.python_environment is not None
    assert (project_path / "pyproject.toml").exists()
    assert (project_path / "src" / "python_project" / "__init__.py").exists()
    assert (project_path / "tests" / "test_python_project.py").exists()
    assert (project_path / INSTRUCTIONS_FILE).exists()
    assert (project_path / PROMPT_TEMPLATES_DIR / "implement.prompt.md").exists()
    assert (project_path / PROMPT_TEMPLATES_DIR / "review.prompt.md").exists()


def test_project_manager_selects_python_environment(tmp_path, monkeypatch):
    """Python environment selection should persist after project creation."""
    monkeypatch.setattr(
        AirunnerPythonEnvironmentService,
        "_create_environment",
        _fake_create_environment,
    )
    recents_path = tmp_path / "recent_workspaces.json"
    project_path = tmp_path / "python-project"
    manager = AirunnerProjectManager(str(recents_path))
    manager.create_python_project(
        str(project_path),
        project_name="Python Project",
    )

    reopened = manager.select_python_environment(
        str(project_path),
        AirunnerPythonEnvironmentSelection(
            manager="venv",
            interpreter_path="/tmp/python-project/.venv/bin/python",
            environment_path="/tmp/python-project/.venv",
            python_version="3.13",
            activate_command="source .venv/bin/activate",
        ),
    )

    assert reopened.ok
    assert reopened.settings.python_environment is not None
    assert reopened.settings.python_environment.manager == "venv"


def test_python_environment_service_uses_darklock_safe_creation(
    tmp_path,
    monkeypatch,
):
    """Local venv creation should allow interpreter access explicitly."""
    project_path = tmp_path / "python-project"
    project_path.mkdir()
    service = AirunnerProjectService(str(project_path))
    env_service = AirunnerPythonEnvironmentService(service)
    selection = AirunnerPythonEnvironmentSelection.for_local_venv(
        str(project_path)
    )
    captured = {}

    class FakeBuilder:
        def __init__(self, *, with_pip, symlinks):
            captured["with_pip"] = with_pip
            captured["symlinks"] = symlinks

        def create(self, environment_path):
            captured["environment_path"] = environment_path

    @contextmanager
    def fake_override(paths=None, allow_any=False):
        captured["override_paths"] = list(paths or [])
        captured["allow_any"] = allow_any
        yield

    monkeypatch.setattr(
        python_environment_service_module.venv,
        "EnvBuilder",
        FakeBuilder,
    )
    monkeypatch.setattr(
        python_environment_service_module.darklock_os,
        "user_override",
        fake_override,
    )
    monkeypatch.setattr(
        python_environment_service_module.sys,
        "executable",
        "/tmp/airunner/python",
    )
    monkeypatch.setattr(
        python_environment_service_module.sys,
        "_base_executable",
        "/usr/bin/python3.13",
        raising=False,
    )

    env_service._create_environment(selection)

    assert captured["with_pip"] is True
    assert captured["symlinks"] is True
    assert captured["environment_path"] == selection.environment_path
    assert captured["allow_any"] is False
    assert "/tmp/airunner/python" in captured["override_paths"]
    assert "/usr/bin/python3.13" in captured["override_paths"]
    assert any(
        path.endswith("/python3.13/venv")
        for path in captured["override_paths"]
    )
    assert any(
        path.endswith("/python3.13/ensurepip")
        for path in captured["override_paths"]
    )


def test_python_environment_service_rebuilds_incomplete_venv(
    tmp_path,
    monkeypatch,
):
    """Incomplete local venvs should be rebuilt before reuse."""
    project_path = tmp_path / "python-project"
    project_path.mkdir()
    service = AirunnerProjectService(str(project_path))
    service.initialize(
        project_name="Python Project",
        settings=AirunnerProjectSettings(
            bootstrap_profile="python-package",
        ),
    )
    env_service = AirunnerPythonEnvironmentService(service)
    selection = AirunnerPythonEnvironmentSelection.for_local_venv(
        str(project_path)
    )
    interpreter = Path(selection.interpreter_path)
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    stale_file = Path(selection.resolved_environment_path()) / "stale.txt"
    stale_file.write_text("stale\n", encoding="utf-8")

    class FakeBuilder:
        def create(self, environment_path):
            env_path = Path(environment_path)
            scripts_dir = env_path / ("Scripts" if os.name == "nt" else "bin")
            scripts_dir.mkdir(parents=True, exist_ok=True)
            python_name = "python.exe" if os.name == "nt" else "python"
            activate_name = "activate.bat" if os.name == "nt" else "activate"
            (scripts_dir / python_name).write_text(
                "#!/usr/bin/env python\n",
                encoding="utf-8",
            )
            (scripts_dir / activate_name).write_text(
                "activate\n",
                encoding="utf-8",
            )
            (env_path / "pyvenv.cfg").write_text(
                "home = /usr/bin\n",
                encoding="utf-8",
            )

    monkeypatch.setattr(env_service, "_env_builder", lambda: FakeBuilder())

    rebuilt = env_service.ensure_environment()

    assert rebuilt is not None
    assert not stale_file.exists()
    assert Path(selection.interpreter_path).exists()
    assert selection.activate_script_exists()
    assert selection.configuration_exists()
    assert selection.is_ready()