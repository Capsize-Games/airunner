"""Higher-level validation coverage for coding workspace workflows."""

import time

from airunner.components.agents.runtime import AgentMessageChannel
from airunner.components.agents.runtime import AgentMessageRecord
from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentRunRecord
from airunner.components.agents.runtime import AgentRunStatus
from airunner.components.document_editor.project import (
    AirunnerAutonomyMode,
    AirunnerProjectManager,
    AirunnerProjectSettings,
    AirunnerProjectStateService,
    AirunnerTrustLevel,
)
from airunner.components.llm.tools.project_context_tools import (
    project_build_context_index,
    project_compact_run,
    project_query_context_index,
)
from airunner.components.llm.tools.project_runtime_tools import (
    project_run_python_lint,
)
from airunner.components.llm.tools.project_runtime_tools_handler import (
    ProjectRuntimeToolsHandler,
)


def _wait_for(predicate, timeout: float = 5.0) -> None:
    """Wait until a condition is true or raise an assertion error."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for condition")


def test_coding_workspace_validation_flow(tmp_path):
    """Core coding-workspace tools should work together in one flow."""
    recents_path = tmp_path / "recent_workspaces.json"
    project_path = tmp_path / "flow-project"
    manager = AirunnerProjectManager(str(recents_path))
    created = manager.create_python_project(
        str(project_path),
        project_name="Flow Project",
        package_name="flow_project",
        settings=AirunnerProjectSettings(
            trust_level=AirunnerTrustLevel.TRUSTED,
            autonomy_mode=AirunnerAutonomyMode.FULL_AUTONOMY,
        ),
    )
    state_service = AirunnerProjectStateService(created.service)
    run = AgentRunRecord(
        session_id="session-1",
        task_id="task-1",
        role=AgentRole.CODER,
        status=AgentRunStatus.RUNNING,
    )
    for index in range(4):
        run.add_message(
            AgentMessageRecord(
                content=f"Flow message {index}",
                channel=AgentMessageChannel.COMMENTARY,
                role=AgentRole.CODER,
            )
        )
    state_service.save_run(run)
    handler = ProjectRuntimeToolsHandler(str(project_path))

    built = project_build_context_index(str(project_path))
    queried = project_query_context_index(str(project_path), "flow project")
    lint = project_run_python_lint(str(project_path))
    _wait_for(
        lambda: not handler.read_terminal_output(lint["session_id"])[
            "is_running"
        ]
    )
    compacted = project_compact_run(
        str(project_path),
        run.record_id,
        max_messages=2,
    )
    restored_run = state_service.load_run(run.record_id)

    assert created.ok
    assert built["success"] is True
    assert queried["match_count"] >= 1
    assert lint["success"] is True
    assert compacted["success"] is True
    assert len(restored_run.messages) == 2
    assert "Compacted 2 earlier messages" in restored_run.summary