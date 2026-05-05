"""Focused tests for .airunner project state persistence."""

from airunner.components.agents.runtime import AgentMessageChannel
from airunner.components.agents.runtime import AgentGeneratedWriteRecord
from airunner.components.agents.runtime import AgentHandoffRecord
from airunner.components.agents.runtime import AgentMessageRecord
from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentRunRecord
from airunner.components.agents.runtime import AgentRunStatus
from airunner.components.agents.runtime import AgentSessionRecord
from airunner.components.agents.runtime import AgentTaskRecord
from airunner.components.agents.runtime import AgentTaskStatus
from airunner.components.agents.runtime import AgentToolCallRecord
from airunner.components.document_editor.project import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)


def test_project_state_service_reads_and_writes_markdown(tmp_path):
    """Plans and memory should persist under the .airunner project tree."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)

    state_service.write_plan("implementation", "# Plan\n")
    state_service.write_memory("notes", "Remember to audit writes.")

    assert state_service.read_plan("implementation") == "# Plan\n"
    assert state_service.read_memory("notes") == (
        "Remember to audit writes.\n"
    )


def test_project_state_service_persists_run_session_and_task_ledgers(
    tmp_path,
):
    """Session, task, and run state should persist for restart recovery."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)

    session = AgentSessionRecord(
        project_path=str(project_service.project_path),
        title="Persistent coding session",
        status=AgentRunStatus.RUNNING,
    )
    task = AgentTaskRecord(
        title="Track tool activity",
        role=AgentRole.CODER,
        session_id=session.record_id,
        status=AgentTaskStatus.IN_PROGRESS,
    )
    run = AgentRunRecord(
        session_id=session.record_id,
        task_id=task.record_id,
        role=AgentRole.CODER,
        status=AgentRunStatus.RUNNING,
    )

    state_service.save_session(session)
    state_service.save_task(task)
    state_service.save_run(run)
    state_service.append_message(
        run.record_id,
        AgentMessageRecord(
            content="Searching the project.",
            channel=AgentMessageChannel.COMMENTARY,
            role=AgentRole.CODER,
        ),
    )
    state_service.append_tool_call(
        run.record_id,
        AgentToolCallRecord(
            tool_name="grep_search",
            arguments={"query": "run_script"},
            output={"matches": 1},
        ),
    )

    restored_session = state_service.load_session(session.record_id)
    restored_task = state_service.load_task(task.record_id)
    restored_run = state_service.load_run(run.record_id)
    resumable_sessions = state_service.list_resumable_sessions()

    assert restored_session.status is AgentRunStatus.RUNNING
    assert restored_task.status is AgentTaskStatus.IN_PROGRESS
    assert restored_run.messages[0].content == "Searching the project."
    assert restored_run.tool_calls[0].tool_name == "grep_search"
    assert [item.record_id for item in resumable_sessions] == [
        session.record_id
    ]


def test_project_state_service_persists_agent_handoffs(tmp_path):
    """Agent handoff artifacts should persist under the .airunner tree."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)

    handoff = AgentHandoffRecord(
        session_id="session-1",
        source_task_id="task-1",
        target_task_id="task-2",
        from_role=AgentRole.PLANNER,
        to_role=AgentRole.REVIEWER,
        summary="Review the planned edits before implementation.",
        artifact_paths=[".airunner/plans/runtime.md"],
    )

    state_service.save_handoff(handoff)

    restored = state_service.load_handoff(handoff.record_id)
    listed = state_service.list_handoffs("session-1")

    assert restored.to_role is AgentRole.REVIEWER
    assert restored.artifact_paths == [".airunner/plans/runtime.md"]
    assert [item.record_id for item in listed] == [handoff.record_id]


def test_project_state_service_persists_generated_write_records(tmp_path):
    """Generated-write audit records should persist under .airunner/audit."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)

    generated_write = AgentGeneratedWriteRecord(
        operation="project_edit_file",
        summary="Edited workspace:src/app.py (+1/-1 lines).",
        run_id="run-1",
        root_name="workspace",
        rel_path="src/app.py",
        target_root_name="workspace",
        target_rel_path="src/app.py",
        before_exists=True,
        after_exists=True,
        before_content="value = 1\n",
        after_content="value = 2\n",
        diff="--- workspace:src/app.py\n+++ workspace:src/app.py",
    )

    state_service.save_generated_write(generated_write)

    restored = state_service.load_generated_write(generated_write.record_id)
    listed = state_service.list_generated_writes("run-1")

    assert restored.operation == "project_edit_file"
    assert restored.after_content == "value = 2\n"
    assert [item.record_id for item in listed] == [generated_write.record_id]