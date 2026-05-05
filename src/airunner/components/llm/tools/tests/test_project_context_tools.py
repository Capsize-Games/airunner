"""Tests for project context index and run-compaction tools."""

from airunner.components.agents.runtime import AgentMessageChannel
from airunner.components.agents.runtime import AgentMessageRecord
from airunner.components.agents.runtime import AgentRole
from airunner.components.agents.runtime import AgentRunRecord
from airunner.components.agents.runtime import AgentRunStatus
from airunner.components.document_editor.project import (
    AirunnerAutonomyMode,
    AirunnerProjectService,
    AirunnerProjectSettings,
    AirunnerProjectStateService,
    AirunnerTrustLevel,
)
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.components.llm.core.tool_registry import ToolRegistry
from airunner.components.llm.tools.project_context_tools import (
    project_build_context_index,
    project_compact_run,
    project_query_context_index,
)


def _trusted_project(tmp_path) -> tuple[AirunnerProjectService, AgentRunRecord]:
    project_service = AirunnerProjectService(str(tmp_path / "context-project"))
    project_service.initialize(
        project_name="Context Project",
        settings=AirunnerProjectSettings(
            trust_level=AirunnerTrustLevel.TRUSTED,
            autonomy_mode=AirunnerAutonomyMode.FULL_AUTONOMY,
        ),
    )
    state_service = AirunnerProjectStateService(project_service)
    project_service.write_file(
        "src/context.py",
        '"""Context helpers."""\n\ndef build_index() -> None:\n    return None\n',
    )
    state_service.write_plan("indexing", "# Indexing\nBuild project context index\n")
    run = AgentRunRecord(
        session_id="session-1",
        task_id="task-1",
        role=AgentRole.CODER,
        status=AgentRunStatus.RUNNING,
    )
    for index in range(4):
        run.add_message(
            AgentMessageRecord(
                content=f"Context message {index}",
                channel=AgentMessageChannel.COMMENTARY,
                role=AgentRole.CODER,
            )
        )
    state_service.save_run(run)
    return project_service, run


def test_project_context_tools_build_query_and_compact(tmp_path):
    """Context tools should index project artifacts and compact runs."""
    project_service, run = _trusted_project(tmp_path)

    built = project_build_context_index(str(project_service.project_path))
    queried = project_query_context_index(
        str(project_service.project_path),
        "index project context",
    )
    compacted = project_compact_run(
        str(project_service.project_path),
        run.record_id,
        max_messages=2,
    )

    assert built["success"] is True
    assert built["entry_count"] >= 2
    assert queried["success"] is True
    assert queried["match_count"] >= 1
    assert "index" in queried["context"].lower()
    assert compacted["success"] is True
    assert compacted["message_count"] == 2
    assert "Compacted 2 earlier messages" in compacted["summary"]


def test_project_context_tools_require_review_for_writes(tmp_path):
    """Review-first projects should gate index builds and run compaction."""
    project_service = AirunnerProjectService(str(tmp_path / "context-project"))
    project_service.initialize(project_name="Context Project")
    state_service = AirunnerProjectStateService(project_service)
    run = AgentRunRecord(
        session_id="session-1",
        task_id="task-1",
        role=AgentRole.CODER,
    )
    state_service.save_run(run)

    blocked_index = project_build_context_index(
        str(project_service.project_path),
    )
    blocked_compaction = project_compact_run(
        str(project_service.project_path),
        run.record_id,
    )

    assert blocked_index["success"] is False
    assert blocked_compaction["success"] is False


def test_project_context_tools_are_registered():
    """Context tools should be registered in the project tool category."""
    expected_tools = [
        "project_build_context_index",
        "project_query_context_index",
        "project_compact_run",
    ]

    for tool_name in expected_tools:
        tool = ToolRegistry.get(tool_name)
        assert tool is not None
        assert tool.category == ToolCategory.PROJECT