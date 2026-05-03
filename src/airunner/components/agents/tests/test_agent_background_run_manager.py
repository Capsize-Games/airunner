"""Focused tests for the resumable background agent runner."""

import time

from PySide6.QtCore import QCoreApplication

from airunner.components.agents.runtime import AgentBackgroundRunManager
from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentRunRecord
from airunner.components.agents.runtime import AgentRunStatus
from airunner.components.agents.runtime import AgentSessionRecord
from airunner.components.agents.runtime import AgentTaskRecord
from airunner.components.agents.runtime import AgentTaskStatus
from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)


def _get_app() -> QCoreApplication:
    """Return a Qt application instance for background-thread signals."""
    app = QCoreApplication.instance()
    if app is not None:
        return app
    return QCoreApplication([])


def _pump_until(predicate, timeout: float = 5.0) -> None:
    """Process Qt events until a condition is true or time runs out."""
    app = _get_app()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for background run condition")


def _build_project_state(tmp_path):
    """Create a coding project service and state service for tests."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)
    session = AgentSessionRecord(
        project_path=str(project_service.project_path),
        title="Background run test session",
    )
    task = AgentTaskRecord(
        title="Execute scripted run",
        role=AgentRole.CODER,
        session_id=session.record_id,
    )
    state_service.save_session(session)
    state_service.save_task(task)
    return state_service, session, task


def test_background_run_manager_completes_and_persists_history(tmp_path):
    """Completed scripted runs should stream status and persist history."""
    _get_app()
    state_service, session, task = _build_project_state(tmp_path)
    manager = AgentBackgroundRunManager()
    progress_updates = []
    status_updates = []
    messages = []
    finished_payloads = []
    manager.runProgressUpdated.connect(
        lambda run_id, value: progress_updates.append((run_id, value))
    )
    manager.runStatusUpdated.connect(
        lambda run_id, status: status_updates.append((run_id, status))
    )
    manager.runMessageLogged.connect(
        lambda run_id, channel, content: messages.append(
            (run_id, channel, content)
        )
    )
    manager.runFinished.connect(
        lambda run_id, payload: finished_payloads.append((run_id, payload))
    )

    run_id = manager.start_scripted_run(
        state_service,
        session,
        task,
        AgentRole.CODER,
        steps=[
            {
                "status": "indexing workspace",
                "progress": 25,
                "commentary": "Scanning files.",
                "delay_seconds": 0.02,
            },
            {
                "status": "writing summary",
                "progress": 100,
                "commentary": "Finished the scripted run.",
                "delay_seconds": 0.02,
            },
        ],
        summary="Test scripted run",
    )

    _pump_until(
        lambda: state_service.load_run(run_id).status
        == AgentRunStatus.COMPLETED
    )
    _pump_until(lambda: len(finished_payloads) == 1)

    restored_session = state_service.load_session(session.record_id)
    restored_task = state_service.load_task(task.record_id)
    restored_run = state_service.load_run(run_id)

    assert restored_session.status is AgentRunStatus.COMPLETED
    assert restored_session.active_run_id is None
    assert restored_task.status is AgentTaskStatus.COMPLETED
    assert restored_run.messages[-1].content == "Finished the scripted run."
    assert progress_updates[-1] == (run_id, 100)
    assert status_updates[-1] == (run_id, AgentRunStatus.COMPLETED.value)
    assert messages[-1] == (
        run_id,
        "commentary",
        "Finished the scripted run.",
    )


def test_background_run_manager_pause_resume_and_cancel(tmp_path):
    """Scripted runs should support pause, resume, and cancel."""
    _get_app()
    state_service, session, task = _build_project_state(tmp_path)
    manager = AgentBackgroundRunManager()

    run_id = manager.start_scripted_run(
        state_service,
        session,
        task,
        AgentRole.CODER,
        steps=[
            {
                "status": "long step",
                "progress": 10,
                "commentary": "Holding for pause.",
                "delay_seconds": 0.3,
            },
            {
                "status": "second step",
                "progress": 60,
                "commentary": "Resumed execution.",
                "delay_seconds": 0.3,
            },
        ],
    )
    _pump_until(
        lambda: state_service.load_run(run_id).messages,
    )

    assert manager.pause_run(run_id)
    _pump_until(
        lambda: state_service.load_run(run_id).status == AgentRunStatus.PAUSED
    )
    assert state_service.load_task(task.record_id).status is AgentTaskStatus.BLOCKED

    assert manager.resume_run(run_id)
    _pump_until(
        lambda: state_service.load_run(run_id).status == AgentRunStatus.RUNNING
    )

    assert manager.cancel_run(run_id)
    _pump_until(
        lambda: state_service.load_run(run_id).status
        == AgentRunStatus.CANCELLED
    )
    _pump_until(lambda: state_service.load_session(session.record_id).active_run_id is None)

    assert state_service.load_task(task.record_id).status is AgentTaskStatus.CANCELLED


def test_background_run_manager_restores_paused_run(tmp_path):
    """Paused runs should be restorable after manager recreation."""
    _get_app()
    state_service, session, task = _build_project_state(tmp_path)
    task.status = AgentTaskStatus.BLOCKED
    session.status = AgentRunStatus.PAUSED
    run = AgentRunRecord(
        session_id=session.record_id,
        task_id=task.record_id,
        role=AgentRole.REVIEWER,
        status=AgentRunStatus.PAUSED,
        metadata={
            "steps": [
                {
                    "status": "waiting to resume",
                    "progress": 50,
                    "commentary": "Paused before completion.",
                    "delay_seconds": 0.3,
                },
                {
                    "status": "finishing",
                    "progress": 100,
                    "commentary": "Restored and completed.",
                    "delay_seconds": 0.02,
                },
            ],
            "current_step_index": 0,
        },
    )
    session.active_run_id = run.record_id
    state_service.save_task(task)
    state_service.save_run(run)
    state_service.save_session(session)

    restored_manager = AgentBackgroundRunManager()
    restored_ids = restored_manager.restore_unfinished_runs(state_service)

    assert restored_ids == [run.record_id]
    assert restored_manager.resume_run(run.record_id)
    _pump_until(
        lambda: state_service.load_run(run.record_id).status
        == AgentRunStatus.COMPLETED
    )
    _pump_until(
        lambda: state_service.load_task(task.record_id).status
        == AgentTaskStatus.COMPLETED
    )
    assert state_service.load_task(task.record_id).status is AgentTaskStatus.COMPLETED