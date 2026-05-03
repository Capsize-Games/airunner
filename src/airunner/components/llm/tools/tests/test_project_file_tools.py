"""Tests for project-aware file tools and auditing."""

from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentRunRecord
from airunner.components.agents.runtime import AgentRunStatus
from airunner.components.agents.runtime import AgentSessionRecord
from airunner.components.agents.runtime import AgentTaskRecord
from airunner.components.agents.runtime import AgentTaskStatus
from airunner.components.document_editor.project import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.components.llm.core.tool_registry import ToolRegistry
from airunner.components.llm.tools.project_file_tools import (
    project_create_file,
    project_edit_file,
    project_get_generated_write_diff,
    project_list_generated_writes,
    project_revert_generated_write,
)
from airunner.components.llm.tools.project_operations_handler import (
    ProjectOperationsHandler,
)


def _build_project(tmp_path) -> tuple[AirunnerProjectService, str]:
    """Create a coding project with one additional workspace root."""
    extra_root = tmp_path / "shared-root"
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(
        project_name="Demo Project",
        additional_roots=[str(extra_root)],
    )
    root_names = [root.name for root in project_service.list_roots()]
    shared_root = next(name for name in root_names if name != "workspace")
    return project_service, shared_root


def _build_run(
    state_service: AirunnerProjectStateService,
    project_path: str,
) -> AgentRunRecord:
    """Create one persisted run ledger for tool-call auditing."""
    session = AgentSessionRecord(
        project_path=project_path,
        title="Project tool audit session",
        status=AgentRunStatus.RUNNING,
    )
    task = AgentTaskRecord(
        title="Track project file tools",
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


def test_project_operations_handler_lists_and_searches_across_roots(
    tmp_path,
):
    """List and search operations should see all configured roots."""
    project_service, shared_root = _build_project(tmp_path)
    project_service.write_file(
        "src/app.py",
        "def hello_workspace():\n    return 'workspace'\n",
    )
    project_service.write_file(
        "lib/shared.py",
        "def hello_shared():\n    return 'shared'\n",
        shared_root,
    )

    handler = ProjectOperationsHandler(str(project_service.project_path))
    listed = handler.list_files(pattern="*.py")
    searched = handler.search_files(
        "hello",
        include_pattern="*.py",
        max_results=10,
    )

    assert listed.success is True
    assert {"root_name": "workspace", "rel_path": "src/app.py"} in listed.files
    assert {"root_name": shared_root, "rel_path": "lib/shared.py"} in listed.files
    assert searched.success is True
    assert any(item["root_name"] == "workspace" for item in searched.matches)
    assert any(item["root_name"] == shared_root for item in searched.matches)


def test_project_operations_handler_audits_writes_and_run_history(
    tmp_path,
):
    """Write operations should emit tool-call audit records and run history."""
    project_service, shared_root = _build_project(tmp_path)
    state_service = AirunnerProjectStateService(project_service)
    run = _build_run(state_service, str(project_service.project_path))
    handler = ProjectOperationsHandler(
        str(project_service.project_path),
        run_id=run.record_id,
    )

    created = handler.create_file("src/demo.py", "value = 1\n")
    edited = handler.edit_file("src/demo.py", "value = 2\n", backup=False)
    patched = handler.patch_file(
        "src/demo.py",
        "value = 2",
        "value = 3",
        backup=False,
    )
    renamed = handler.rename_file(
        "src/demo.py",
        "src/final.py",
        new_root_name=shared_root,
    )
    deleted = handler.delete_file(
        "src/final.py",
        root_name=shared_root,
        backup=False,
    )

    recorded = state_service.load_tool_call(created.audit_record_id)
    run_record = state_service.load_run(run.record_id)
    generated_writes = state_service.list_generated_writes(run.record_id)

    assert created.success is True
    assert edited.success is True
    assert patched.success is True
    assert renamed.success is True
    assert deleted.success is True
    assert recorded.tool_name == "project_create_file"
    assert recorded.arguments["rel_path"] == "src/demo.py"
    assert [call.tool_name for call in run_record.tool_calls] == [
        "project_create_file",
        "project_edit_file",
        "project_patch_file",
        "project_rename_file",
        "project_delete_file",
    ]
    assert len(state_service.list_tool_calls()) == 5
    assert len(generated_writes) == 5
    assert any(item.operation == "project_patch_file" for item in generated_writes)


def test_project_review_tools_show_diffs_and_revert_writes(tmp_path):
    """Generated-write review tools should expose diffs and rollback."""
    project_service, _ = _build_project(tmp_path)
    state_service = AirunnerProjectStateService(project_service)
    run = _build_run(state_service, str(project_service.project_path))

    created = project_create_file(
        str(project_service.project_path),
        "notes/todo.md",
        "- original\n",
        run_id=run.record_id,
    )
    edited = project_edit_file(
        str(project_service.project_path),
        "notes/todo.md",
        "- updated\n",
        run_id=run.record_id,
    )

    listed = project_list_generated_writes(
        str(project_service.project_path),
        run_id=run.record_id,
    )
    diff = project_get_generated_write_diff(
        str(project_service.project_path),
        edited["details"]["generated_write_id"],
        run_id=run.record_id,
    )
    reverted = project_revert_generated_write(
        str(project_service.project_path),
        edited["details"]["generated_write_id"],
        run_id=run.record_id,
    )

    assert created["success"] is True
    assert edited["success"] is True
    assert listed["success"] is True
    assert len(listed["details"]["generated_writes"]) == 2
    assert diff["success"] is True
    assert "+++ workspace:notes/todo.md" in diff["content"]
    assert reverted["success"] is True
    assert state_service.load_generated_write(
        edited["details"]["generated_write_id"]
    ).metadata["reverted_at"]
    assert project_service.read_file("notes/todo.md") == "- original\n"


def test_project_tools_are_registered_and_callable(tmp_path):
    """Project-aware tools should be registered in the tool registry."""
    expected_tools = [
        "project_list_files",
        "project_read_file",
        "project_search_files",
        "project_create_file",
        "project_edit_file",
        "project_patch_file",
        "project_rename_file",
        "project_delete_file",
        "project_list_generated_writes",
        "project_get_generated_write_diff",
        "project_revert_generated_write",
    ]

    for tool_name in expected_tools:
        tool = ToolRegistry.get(tool_name)
        assert tool is not None
        assert tool.category == ToolCategory.PROJECT

    project_service, _ = _build_project(tmp_path)
    result = project_create_file(
        str(project_service.project_path),
        "notes/todo.md",
        "- wire audit hooks\n",
    )

    assert result["success"] is True
    assert result["audit_record_id"]