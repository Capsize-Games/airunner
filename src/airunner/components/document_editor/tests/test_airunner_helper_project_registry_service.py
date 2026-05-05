"""Tests for the helper-project registry service."""

from pathlib import Path

import pytest

from airunner.components.document_editor.project import (
    AirunnerHelperProjectRecord,
    AirunnerHelperProjectRegistryService,
    AirunnerProjectService,
)
from airunner.components.document_editor.project.airunner_project_paths import (
    HELPER_PROJECT_FILE,
)


def _create_helper_project(project_path: Path) -> None:
    """Initialize one helper project for registry tests."""
    service = AirunnerProjectService(str(project_path))
    service.initialize(project_name=project_path.name)


def test_helper_project_registry_registers_and_loads_metadata(tmp_path):
    """Helper projects should persist searchable metadata."""
    projects_root = tmp_path / "Projects"
    project_path = projects_root / "brief-table-extractor"
    _create_helper_project(project_path)
    registry = AirunnerHelperProjectRegistryService(str(projects_root))

    saved = registry.register_project(
        str(project_path),
        AirunnerHelperProjectRecord(
            name="brief-table-extractor",
            description="Extracts comparison tables from brief notes",
            workflow_kind="research-brief",
            input_contract="Research notes markdown",
            output_contract="JSON table rows",
            origin_artifact="brief-package",
            reuse_notes="Reuse for competitive matrices.",
            tags=("research", "tables"),
        ),
    )
    loaded = registry.load_project(str(project_path))

    assert loaded == saved
    assert loaded is not None
    assert loaded.created_at
    assert loaded.updated_at
    assert (project_path / HELPER_PROJECT_FILE).exists()


def test_helper_project_registry_lists_only_registered_projects(tmp_path):
    """Listing should include only projects with helper metadata."""
    projects_root = tmp_path / "Projects"
    registered_path = projects_root / "registered-helper"
    plain_path = projects_root / "plain-helper"
    _create_helper_project(registered_path)
    _create_helper_project(plain_path)
    registry = AirunnerHelperProjectRegistryService(str(projects_root))
    registry.register_project(
        str(registered_path),
        AirunnerHelperProjectRecord(
            name="registered-helper",
            description="Builds brief appendix tables",
            workflow_kind="research-brief",
            input_contract="Evidence JSON",
            output_contract="Markdown appendix",
        ),
    )

    projects = registry.list_projects()

    assert len(projects) == 1
    assert projects[0][0] == str(registered_path)
    assert projects[0][1].name == "registered-helper"


def test_helper_project_registry_searches_tags_and_description(tmp_path):
    """Search should rank helper projects by metadata relevance."""
    projects_root = tmp_path / "Projects"
    table_path = projects_root / "brief-table-extractor"
    email_path = projects_root / "meeting-followup-writer"
    _create_helper_project(table_path)
    _create_helper_project(email_path)
    registry = AirunnerHelperProjectRegistryService(str(projects_root))
    registry.register_project(
        str(table_path),
        AirunnerHelperProjectRecord(
            name="brief-table-extractor",
            description="Extracts research comparison tables",
            workflow_kind="research-brief",
            input_contract="Brief markdown",
            output_contract="JSON rows",
            tags=("research", "tables"),
        ),
    )
    registry.register_project(
        str(email_path),
        AirunnerHelperProjectRecord(
            name="meeting-followup-writer",
            description="Drafts follow-up emails from meeting notes",
            workflow_kind="meeting",
            input_contract="Meeting notes",
            output_contract="Email draft markdown",
            tags=("meeting", "email"),
        ),
    )

    matches = registry.search_projects(
        "research tables",
        workflow_kind="research-brief",
    )

    assert len(matches) == 1
    assert matches[0][0] == str(table_path)
    assert matches[0][1].name == "brief-table-extractor"


def test_helper_project_registry_records_last_use(tmp_path):
    """Reusing a helper project should update the last-used timestamp."""
    projects_root = tmp_path / "Projects"
    project_path = projects_root / "brief-table-extractor"
    _create_helper_project(project_path)
    registry = AirunnerHelperProjectRegistryService(str(projects_root))
    registry.register_project(
        str(project_path),
        AirunnerHelperProjectRecord(
            name="brief-table-extractor",
            description="Extracts research comparison tables",
            workflow_kind="research-brief",
            input_contract="Brief markdown",
            output_contract="JSON rows",
        ),
    )

    updated = registry.record_use(str(project_path))

    assert updated.last_used_at
    assert updated.updated_at == updated.last_used_at


def test_helper_project_registry_rejects_paths_outside_projects_root(
    tmp_path,
):
    """Registry writes should stay inside the AIRunner Projects root."""
    projects_root = tmp_path / "Projects"
    project_path = tmp_path / "outside-helper"
    _create_helper_project(project_path)
    registry = AirunnerHelperProjectRegistryService(str(projects_root))

    with pytest.raises(ValueError):
        registry.register_project(
            str(project_path),
            AirunnerHelperProjectRecord(
                name="outside-helper",
                description="Should not register outside the root",
                workflow_kind="research-brief",
                input_contract="input",
                output_contract="output",
            ),
        )