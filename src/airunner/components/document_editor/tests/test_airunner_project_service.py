"""Unit tests for AIRunner coding-project metadata and services."""

import os

import pytest

from airunner.components.document_editor.project import (
    AirunnerAutonomyMode,
    AirunnerProjectPolicyEnforcer,
    AirunnerProjectRoot,
    AirunnerProjectService,
    AirunnerProjectSettings,
    AirunnerTrustLevel,
    AirunnerWorkspaceConfig,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    SETTINGS_FILE,
    WORKSPACE_FILE,
    required_project_directories,
)


def test_project_settings_reject_untrusted_autonomy_modes():
    """Untrusted projects must not bypass review-first autonomy."""
    settings = AirunnerProjectSettings(
        trust_level=AirunnerTrustLevel.UNTRUSTED,
        autonomy_mode=AirunnerAutonomyMode.FULL_AUTONOMY,
    )

    assert settings.validate() == [
        "Untrusted projects must use review-first autonomy mode."
    ]


def test_project_policy_enforcer_reports_mode_requirements(tmp_path):
    """Policy decisions should reflect the persisted autonomy mode."""
    review_service = AirunnerProjectService(str(tmp_path / "review-project"))
    review_service.initialize(project_name="Review Project")
    review_enforcer = AirunnerProjectPolicyEnforcer(review_service)

    mixed_service = AirunnerProjectService(str(tmp_path / "mixed-project"))
    mixed_service.initialize(
        project_name="Mixed Project",
        settings=AirunnerProjectSettings(
            trust_level=AirunnerTrustLevel.TRUSTED,
            autonomy_mode=AirunnerAutonomyMode.MIXED,
        ),
    )
    mixed_enforcer = AirunnerProjectPolicyEnforcer(mixed_service)

    full_service = AirunnerProjectService(str(tmp_path / "full-project"))
    full_service.initialize(
        project_name="Full Project",
        settings=AirunnerProjectSettings(
            trust_level=AirunnerTrustLevel.TRUSTED,
            autonomy_mode=AirunnerAutonomyMode.FULL_AUTONOMY,
        ),
    )
    full_enforcer = AirunnerProjectPolicyEnforcer(full_service)

    assert not review_enforcer.command_decision().allowed
    assert not review_enforcer.file_write_decision().allowed
    assert mixed_enforcer.command_decision().allowed
    assert not mixed_enforcer.file_write_decision().allowed
    assert full_enforcer.command_decision().allowed
    assert full_enforcer.file_write_decision().allowed


def test_workspace_config_round_trips_multiple_roots():
    """Workspace configs should preserve multiple roots on round trip."""
    roots = [
        AirunnerProjectRoot(name="workspace", path="."),
        AirunnerProjectRoot(name="shared", path="/tmp/shared"),
    ]
    workspace = AirunnerWorkspaceConfig.create_default("Demo", roots)

    loaded = AirunnerWorkspaceConfig.from_dict(workspace.to_dict())

    assert loaded.project_name == "Demo"
    assert loaded.primary_root == "workspace"
    assert loaded.roots == roots


def test_project_service_initializes_airunner_layout(tmp_path):
    """Project initialization should create the .airunner contract."""
    project_path = tmp_path / "demo-project"
    service = AirunnerProjectService(str(project_path))

    workspace, settings = service.initialize(project_name="Demo Project")

    assert service.exists()
    assert workspace.project_name == "Demo Project"
    assert settings.autonomy_mode == AirunnerAutonomyMode.REVIEW_FIRST
    assert (project_path / WORKSPACE_FILE).exists()
    assert (project_path / SETTINGS_FILE).exists()
    for path in required_project_directories():
        assert (project_path / path).is_dir()


def test_project_service_resolves_multiple_roots(tmp_path):
    """Project services should resolve configured root paths cleanly."""
    project_path = tmp_path / "demo-project"
    shared_path = tmp_path / "shared-lib"
    shared_path.mkdir()
    service = AirunnerProjectService(str(project_path))

    workspace, _ = service.initialize(additional_roots=[str(shared_path)])

    shared_root = next(root for root in workspace.roots if root.name != "workspace")
    assert service.resolve_root_path(shared_root.name) == str(shared_path)


def test_project_service_checks_root_membership(tmp_path):
    """Project services should report which root owns a candidate path."""
    project_path = tmp_path / "demo-project"
    shared_path = tmp_path / "shared-lib"
    outside_path = tmp_path / "outside"
    shared_path.mkdir()
    outside_path.mkdir()
    service = AirunnerProjectService(str(project_path))
    workspace, _ = service.initialize(additional_roots=[str(shared_path)])

    shared_root = next(root for root in workspace.roots if root.name != "workspace")
    file_path = shared_path / "module.py"
    file_path.write_text("print('hi')\n", encoding="utf-8")

    assert service.contains_path(str(file_path))
    assert service.root_for_path(str(file_path)) == shared_root
    assert service.project_relative_path(str(file_path)) == (
        shared_root.name,
        "module.py",
    )
    assert not service.contains_path(str(outside_path / "ignored.py"))


def test_project_service_returns_root_workspace_manager(tmp_path):
    """Workspace managers should be available for each configured root."""
    project_path = tmp_path / "demo-project"
    shared_path = tmp_path / "shared-lib"
    shared_path.mkdir()
    service = AirunnerProjectService(str(project_path))
    workspace, _ = service.initialize(additional_roots=[str(shared_path)])

    shared_root = next(root for root in workspace.roots if root.name != "workspace")
    manager = service.get_workspace_manager(shared_root.name)
    manager.write_file("module.py", "print('ok')\n", backup=False)

    assert os.path.exists(shared_path / "module.py")


def test_project_service_rejects_path_escape(tmp_path):
    """Project services should reject file paths outside a declared root."""
    project_path = tmp_path / "demo-project"
    service = AirunnerProjectService(str(project_path))
    service.initialize(project_name="Demo Project")

    with pytest.raises(ValueError):
        service.resolve_path("../escape.py")


def test_project_service_delegates_file_operations(tmp_path):
    """Project services should expose safe file operations per root."""
    project_path = tmp_path / "demo-project"
    shared_path = tmp_path / "shared-lib"
    shared_path.mkdir()
    service = AirunnerProjectService(str(project_path))
    workspace, _ = service.initialize(additional_roots=[str(shared_path)])

    shared_root = next(
        root for root in workspace.roots if root.name != "workspace"
    )

    service.write_file(
        "pkg/module.py",
        "print('shared')\n",
        root_name=shared_root.name,
        backup=False,
    )

    assert service.read_file(
        "pkg/module.py",
        root_name=shared_root.name,
    ) == "print('shared')\n"
    assert service.resolve_path(
        "pkg/module.py",
        root_name=shared_root.name,
    ) == os.path.join(str(shared_path), "pkg", "module.py")
    assert service.list_files(
        root_name=shared_root.name,
        recursive=True,
    ) == ["pkg/module.py"]