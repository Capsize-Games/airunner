"""Unit tests for AIRunner coding-project bootstrap flows."""

from airunner.components.document_editor.project import (
    AirunnerProjectManager,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    PROJECT_DIR_NAME,
)


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