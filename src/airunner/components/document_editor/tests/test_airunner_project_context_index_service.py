"""Focused tests for project context indexing and retrieval."""

from airunner.components.agents.runtime import AgentMessageChannel
from airunner.components.agents.runtime import AgentMessageRecord
from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentRunRecord
from airunner.components.agents.runtime import AgentRunStatus
from airunner.components.document_editor.project import (
    AirunnerProjectContextIndexService,
)
from airunner.components.document_editor.project import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)


def test_project_context_index_service_indexes_workspace_and_airunner_artifacts(
    tmp_path,
):
    """Context indexes should include source files and .airunner artifacts."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)
    project_service.write_file(
        "src/feature.py",
        '"""Feature helpers."""\n\nclass Planner:\n    pass\n',
    )
    state_service.write_plan("implementation", "# Implementation\nPlanner work\n")
    state_service.write_memory("notes", "Remember the planner handoff.")
    state_service.save_run(
        AgentRunRecord(
            session_id="session-1",
            task_id="task-1",
            role=AgentRole.CODER,
            status=AgentRunStatus.COMPLETED,
            summary="Planner handoff completed for feature.py.",
        )
    )
    service = AirunnerProjectContextIndexService(project_service)

    index = service.build_index()
    query = service.query_index("planner handoff", limit=5)

    assert index.entries
    assert any(entry.artifact_type == "source" for entry in index.entries)
    assert any(entry.artifact_type == "plan" for entry in index.entries)
    assert any(entry.artifact_type == "run-summary" for entry in index.entries)
    assert query["match_count"] >= 1
    assert "planner" in query["context"].lower()


def test_project_context_index_service_uses_recent_run_summary_when_missing(
    tmp_path,
):
    """Run entries should fall back to recent message content when needed."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)
    run = AgentRunRecord(
        session_id="session-1",
        task_id="task-1",
        role=AgentRole.REVIEWER,
        status=AgentRunStatus.RUNNING,
    )
    run.add_message(
        AgentMessageRecord(
            content="Reviewing generated writes for planner handoff.",
            channel=AgentMessageChannel.COMMENTARY,
            role=AgentRole.REVIEWER,
        )
    )
    state_service.save_run(run)
    service = AirunnerProjectContextIndexService(project_service)

    result = service.query_index("generated writes", limit=5)

    assert result["match_count"] >= 1
    assert "generated writes" in result["context"].lower()