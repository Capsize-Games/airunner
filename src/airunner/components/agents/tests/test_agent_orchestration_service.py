"""Tests for persistent multi-agent orchestration helpers."""

import pytest

from airunner.components.agents.runtime import AgentOrchestrationService
from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentTaskStatus
from airunner.components.document_editor.project import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)


def _build_orchestration(tmp_path) -> AgentOrchestrationService:
    """Create a project-backed orchestration service for tests."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)
    return AgentOrchestrationService(state_service)


def test_orchestration_service_creates_role_handoff(tmp_path):
    """Planner work should hand off into a persisted coder task."""
    service = _build_orchestration(tmp_path)
    session = service.create_session("Agent collaboration")
    planner_task = service.create_task(
        session.record_id,
        "Draft implementation plan",
        AgentRole.PLANNER,
        artifact_paths=[".airunner/plans/runtime.md"],
        status=AgentTaskStatus.IN_PROGRESS,
    )

    handoff, coder_task = service.handoff_task(
        planner_task.record_id,
        AgentRole.CODER,
        title="Implement the approved plan",
        summary="Use the persisted plan artifact as the implementation source.",
    )

    restored_session = service.state_service.load_session(session.record_id)
    restored_planner = service.state_service.load_task(planner_task.record_id)
    restored_handoff = service.state_service.load_handoff(handoff.record_id)

    assert restored_planner.status is AgentTaskStatus.COMPLETED
    assert coder_task.role is AgentRole.CODER
    assert coder_task.artifact_paths == [".airunner/plans/runtime.md"]
    assert restored_handoff.source_task_id == planner_task.record_id
    assert restored_handoff.target_task_id == coder_task.record_id
    assert restored_session.task_ids == [
        planner_task.record_id,
        coder_task.record_id,
    ]


def test_orchestration_service_rejects_conflicting_artifact_claims(
    tmp_path,
):
    """Active tasks should not silently claim the same artifact paths."""
    service = _build_orchestration(tmp_path)
    session = service.create_session("Collision detection")
    service.create_task(
        session.record_id,
        "Implement main widget",
        AgentRole.CODER,
        artifact_paths=["src/widget.py"],
        status=AgentTaskStatus.IN_PROGRESS,
    )

    with pytest.raises(ValueError):
        service.create_task(
            session.record_id,
            "Review main widget",
            AgentRole.REVIEWER,
            artifact_paths=["src/widget.py"],
        )