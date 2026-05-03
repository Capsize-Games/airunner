"""Tests for project-aware runtime and diagnostics tools."""

import shlex
import sys
import time

from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentRunRecord
from airunner.components.agents.runtime import AgentRunStatus
from airunner.components.agents.runtime import AgentSessionRecord
from airunner.components.agents.runtime import AgentTaskRecord
from airunner.components.agents.runtime import AgentTaskStatus
from airunner.components.document_editor.project import (
    AirunnerAutonomyMode,
    AirunnerProjectService,
)
from airunner.components.document_editor.project import (
    AirunnerProjectSettings,
    AirunnerProjectStateService,
)
from airunner.components.document_editor.project import AirunnerTrustLevel
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.components.llm.core.tool_registry import ToolRegistry
from airunner.components.llm.tools.project_runtime_tools import (
    project_run_command,
    project_get_workspace_summary,
)
from airunner.components.llm.tools.project_runtime_tools_handler import (
    ProjectRuntimeToolsHandler,
)


def _wait_for(predicate, timeout: float = 5.0) -> None:
    """Wait for a condition or raise an assertion error."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for condition")


def _python_command(snippet: str) -> str:
    """Build a shell-safe command string for the current interpreter."""
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(snippet)}"


def _build_project(tmp_path) -> AirunnerProjectService:
    """Create an initialized .airunner project for testing."""
    project_service = AirunnerProjectService(str(tmp_path / "runtime-project"))
    project_service.initialize(
        project_name="Runtime Project",
        settings=AirunnerProjectSettings(
            trust_level=AirunnerTrustLevel.TRUSTED,
            autonomy_mode=AirunnerAutonomyMode.FULL_AUTONOMY,
        ),
    )
    return project_service


def _build_run(
    state_service: AirunnerProjectStateService,
    project_path: str,
) -> AgentRunRecord:
    """Create one persisted run for runtime-tool audit checks."""
    session = AgentSessionRecord(
        project_path=project_path,
        title="Runtime tools session",
        status=AgentRunStatus.RUNNING,
    )
    task = AgentTaskRecord(
        title="Track runtime tools",
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
    return run


def test_project_runtime_handler_runs_command_and_reads_live_output(
    tmp_path,
):
    """Agents should be able to run commands and query live output."""
    project_service = _build_project(tmp_path)
    state_service = AirunnerProjectStateService(project_service)
    run = _build_run(state_service, str(project_service.project_path))
    handler = ProjectRuntimeToolsHandler(
        str(project_service.project_path),
        run_id=run.record_id,
    )

    started = handler.run_command(
        _python_command(
            "import time; print('start'); time.sleep(0.2); print('done')"
        )
    )
    session_id = started["session_id"]

    _wait_for(
        lambda: "done" in handler.read_terminal_output(session_id)["output"]
    )
    _wait_for(lambda: not handler.read_terminal_output(session_id)["is_running"])
    output = handler.read_terminal_output(session_id, limit=4000)
    audit = state_service.load_tool_call(started["audit_record_id"])

    assert started["success"] is True
    assert "start" in output["output"]
    assert "done" in output["output"]
    assert audit.tool_name == "project_run_command"


def test_project_runtime_handler_supports_input_and_stop(tmp_path):
    """Terminal tools should support input and explicit stop requests."""
    project_service = _build_project(tmp_path)
    state_service = AirunnerProjectStateService(project_service)
    run = _build_run(state_service, str(project_service.project_path))
    handler = ProjectRuntimeToolsHandler(
        str(project_service.project_path),
        run_id=run.record_id,
    )

    interactive = handler.run_command(
        _python_command("import sys; print(sys.stdin.readline().strip())")
    )
    input_session = interactive["session_id"]
    sent = handler.send_terminal_input(input_session, "typed through tool")

    _wait_for(
        lambda: "typed through tool"
        in handler.read_terminal_output(input_session)["output"]
    )

    long_running = handler.run_command(
        _python_command("import time; print('alive'); time.sleep(30)")
    )
    stop_session = long_running["session_id"]

    _wait_for(
        lambda: "alive" in handler.read_terminal_output(stop_session)["output"]
    )
    stopped = handler.stop_command(stop_session, timeout=0.2)
    _wait_for(lambda: not handler.read_terminal_output(stop_session)["is_running"])
    run_record = state_service.load_run(run.record_id)

    assert sent["success"] is True
    assert stopped["success"] is True
    assert [call.tool_name for call in run_record.tool_calls] == [
        "project_run_command",
        "project_send_terminal_input",
        "project_run_command",
        "project_stop_command",
    ]


def test_project_runtime_handler_reports_diagnostics_and_summary(
    tmp_path,
):
    """Diagnostics and workspace summary tools should expose coding context."""
    project_service = _build_project(tmp_path)
    project_service.write_file(
        "src/bad.py",
        "def broken(:\n    pass\n",
    )
    project_service.write_file(
        "src/good.py",
        "def good() -> int:\n    return 1\n",
    )
    handler = ProjectRuntimeToolsHandler(str(project_service.project_path))

    diagnostics = handler.diagnostics(rel_paths=["src/bad.py"])
    summary = handler.workspace_summary()

    assert diagnostics["success"] is True
    assert diagnostics["summary"]["files_checked"] == 1
    assert any(item["code"] == "syntax" for item in diagnostics["diagnostics"])
    assert summary["success"] is True
    assert summary["primary_root"] == "workspace"
    assert any(root["file_count"] >= 2 for root in summary["roots"])


def test_project_runtime_tools_block_commands_without_approval_in_review_first(
    tmp_path,
):
    """Review-first projects should block commands until approved."""
    project_service = AirunnerProjectService(str(tmp_path / "runtime-project"))
    project_service.initialize(project_name="Runtime Project")

    blocked = project_run_command(
        str(project_service.project_path),
        _python_command("print('blocked')"),
    )
    allowed = project_run_command(
        str(project_service.project_path),
        _python_command("print('allowed')"),
        approved=True,
    )

    assert blocked["success"] is False
    assert blocked["error"] == "Command approval required for this project."
    assert blocked["details"]["policy"]["autonomy_mode"] == "review-first"
    assert allowed["success"] is True


def test_project_runtime_tools_are_registered_and_callable(tmp_path):
    """Project runtime tools should be registered in the tool registry."""
    expected_tools = [
        "project_run_command",
        "project_read_terminal_output",
        "project_send_terminal_input",
        "project_stop_command",
        "project_list_terminal_sessions",
        "project_get_diagnostics",
        "project_get_workspace_summary",
    ]

    for tool_name in expected_tools:
        tool = ToolRegistry.get(tool_name)
        assert tool is not None
        assert tool.category == ToolCategory.PROJECT

    project_service = _build_project(tmp_path)
    summary = project_get_workspace_summary(str(project_service.project_path))

    assert summary["success"] is True
    assert summary["project_name"] == "Runtime Project"
    assert summary["policy"]["autonomy_mode"] == "full-autonomy"