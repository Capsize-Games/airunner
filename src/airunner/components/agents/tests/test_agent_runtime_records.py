"""Focused tests for persisted coding-agent runtime records."""

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
from airunner.components.agents.runtime import ResearchEvidenceRecord
from airunner.components.agents.runtime import ResearchBriefRecord
from airunner.components.agents.runtime import ResearchReviewStatus
from airunner.components.agents.runtime import ResearchRunRecord
from airunner.components.agents.runtime import ResearchSourceRecord


def test_agent_run_record_round_trips_nested_runtime_history():
    """Run records should round-trip messages and tool calls."""
    run = AgentRunRecord(
        session_id="session-1",
        task_id="task-1",
        role=AgentRole.CODER,
        status=AgentRunStatus.RUNNING,
        summary="Implement workspace shell",
    )
    run.add_message(
        AgentMessageRecord(
            content="Updating the shell panels.",
            channel=AgentMessageChannel.COMMENTARY,
            role=AgentRole.CODER,
        )
    )
    run.add_tool_call(
        AgentToolCallRecord(
            tool_name="apply_patch",
            arguments={"file": "widget.py"},
            output={"ok": True},
        )
    )

    restored = AgentRunRecord.from_dict(run.to_dict())

    assert restored.role is AgentRole.CODER
    assert restored.status is AgentRunStatus.RUNNING
    assert restored.messages[0].channel is AgentMessageChannel.COMMENTARY
    assert restored.tool_calls[0].tool_name == "apply_patch"


def test_agent_run_record_filters_channel_history():
    """Run records should expose per-channel message history."""
    run = AgentRunRecord(
        session_id="session-1",
        task_id="task-1",
        role=AgentRole.REVIEWER,
    )
    run.add_message(
        AgentMessageRecord(
            content="Investigating.",
            channel=AgentMessageChannel.ANALYSIS,
            role=AgentRole.REVIEWER,
        )
    )
    run.add_message(
        AgentMessageRecord(
            content="Found the regression.",
            channel=AgentMessageChannel.FINAL,
            role=AgentRole.REVIEWER,
        )
    )

    final_messages = run.channel_messages(AgentMessageChannel.FINAL)

    assert len(final_messages) == 1
    assert final_messages[0].content == "Found the regression."


def test_session_and_task_records_round_trip():
    """Session and task ledgers should round-trip cleanly."""
    session = AgentSessionRecord(
        project_path="/tmp/demo-project",
        title="Build coding workspace",
        status=AgentRunStatus.PAUSED,
        active_run_id="run-1",
        task_ids=["task-1"],
    )
    task = AgentTaskRecord(
        title="Persist agent state",
        role=AgentRole.PLANNER,
        session_id=session.record_id,
        status=AgentTaskStatus.IN_PROGRESS,
        artifact_paths=[".airunner/plans/runtime.md"],
    )

    restored_session = AgentSessionRecord.from_dict(session.to_dict())
    restored_task = AgentTaskRecord.from_dict(task.to_dict())

    assert restored_session.status is AgentRunStatus.PAUSED
    assert restored_session.active_run_id == "run-1"
    assert restored_task.role is AgentRole.PLANNER
    assert restored_task.status is AgentTaskStatus.IN_PROGRESS


def test_handoff_record_round_trips_between_roles():
    """Handoff artifacts should round-trip cleanly between agent roles."""
    handoff = AgentHandoffRecord(
        session_id="session-1",
        source_task_id="task-1",
        target_task_id="task-2",
        from_role=AgentRole.PLANNER,
        to_role=AgentRole.CODER,
        summary="Planner handed implementation details to the coder.",
        artifact_paths=[".airunner/plans/runtime.md"],
    )

    restored = AgentHandoffRecord.from_dict(handoff.to_dict())

    assert restored.from_role is AgentRole.PLANNER
    assert restored.to_role is AgentRole.CODER
    assert restored.artifact_paths == [".airunner/plans/runtime.md"]


def test_generated_write_record_round_trips_for_review():
    """Generated-write audit records should keep diff review data."""
    record = AgentGeneratedWriteRecord(
        operation="project_edit_file",
        summary="Edited workspace:src/app.py (+1/-1 lines).",
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

    restored = AgentGeneratedWriteRecord.from_dict(record.to_dict())

    assert restored.operation == "project_edit_file"
    assert restored.rel_path == "src/app.py"
    assert "+++ workspace:src/app.py" in restored.diff


def test_agent_run_record_compacts_older_history_into_summary():
    """Run compaction should preserve recent history and summarize older work."""
    run = AgentRunRecord(
        session_id="session-1",
        task_id="task-1",
        role=AgentRole.CODER,
    )
    for index in range(5):
        run.add_message(
            AgentMessageRecord(
                content=f"Message {index}",
                channel=AgentMessageChannel.COMMENTARY,
                role=AgentRole.CODER,
            )
        )
        run.add_tool_call(
            AgentToolCallRecord(
                tool_name=f"tool_{index}",
                arguments={"index": index},
                output={"ok": True},
            )
        )

    run.compact(max_messages=2, max_tool_calls=3)

    assert len(run.messages) == 2
    assert len(run.tool_calls) == 3
    assert "Compacted 3 earlier messages" in run.summary
    assert run.metadata["compaction"]["omitted_tool_calls"] == 2


def test_research_records_round_trip_with_attribution():
    """Research records should preserve statuses and source attribution."""
    research_run = ResearchRunRecord(
        topic="grid resilience",
        query="energy grid resilience recent studies",
        status=AgentRunStatus.RUNNING,
    )
    source = ResearchSourceRecord(
        run_id=research_run.record_id,
        url="https://example.com/report",
        title="Grid Resilience Report",
        status=ResearchReviewStatus.ACCEPTED,
        authors=["Jane Doe"],
    )
    evidence = ResearchEvidenceRecord(
        run_id=research_run.record_id,
        fact_text="Reserve capacity increased by 12 percent.",
        source_ids=[source.record_id],
        status=ResearchReviewStatus.ACCEPTED,
        evidence_kind="numeric_fact",
        numeric_value="12",
        numeric_unit="percent",
        quote_text="Reserve capacity increased by 12 percent.",
    )
    research_run.add_source(source.record_id)
    research_run.add_evidence(evidence.record_id)

    restored_run = ResearchRunRecord.from_dict(research_run.to_dict())
    restored_source = ResearchSourceRecord.from_dict(source.to_dict())
    restored_evidence = ResearchEvidenceRecord.from_dict(evidence.to_dict())

    assert restored_run.status is AgentRunStatus.RUNNING
    assert restored_run.source_ids == [source.record_id]
    assert restored_source.status is ResearchReviewStatus.ACCEPTED
    assert restored_source.authors == ["Jane Doe"]
    assert restored_evidence.source_ids == [source.record_id]
    assert restored_evidence.numeric_value == "12"


def test_research_brief_record_round_trips_export_bundle():
    """Research brief records should preserve export artifact metadata."""
    brief = ResearchBriefRecord(
        run_id="run-1",
        title="Research Brief: Grid Resilience",
        executive_summary="Coverage is 0.75 and confidence is 0.80.",
        supported_findings=["Reserve capacity increased by 12 percent."],
        open_questions=["How durable is the increase beyond 2026?"],
        weak_evidence_ids=["evidence-2"],
        coverage_score=0.75,
        confidence_score=0.8,
        artifact_paths=[
            ".airunner/research/briefs/brief-1.json",
            ".airunner/research/briefs/brief-1.md",
        ],
    )

    restored = ResearchBriefRecord.from_dict(brief.to_dict())

    assert restored.title == "Research Brief: Grid Resilience"
    assert restored.coverage_score == 0.75
    assert restored.artifact_paths[1].endswith("brief-1.md")