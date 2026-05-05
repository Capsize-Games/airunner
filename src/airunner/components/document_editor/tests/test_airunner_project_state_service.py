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
from airunner.components.agents.runtime import MeetingDeliverableRecord
from airunner.components.agents.runtime import MeetingItemRecord
from airunner.components.agents.runtime import MeetingItemStatus
from airunner.components.agents.runtime import MeetingReviewRecord
from airunner.components.agents.runtime import MeetingReviewStatus
from airunner.components.agents.runtime import MeetingRunRecord
from airunner.components.agents.runtime import ResearchEvidenceRecord
from airunner.components.agents.runtime import ResearchBriefRecord
from airunner.components.agents.runtime import ResearchReviewStatus
from airunner.components.agents.runtime import ResearchRunRecord
from airunner.components.agents.runtime import ResearchSourceRecord
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


def test_project_state_service_persists_research_ledgers(tmp_path):
    """Research runs, sources, and evidence should persist separately."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)

    research_run = ResearchRunRecord(
        topic="grid resilience",
        query="energy grid resilience recent studies",
        status=AgentRunStatus.RUNNING,
    )
    state_service.save_research_run(research_run)

    accepted_source = ResearchSourceRecord(
        run_id=research_run.record_id,
        url="https://example.com/accepted",
        title="Accepted source",
        status=ResearchReviewStatus.ACCEPTED,
    )
    rejected_source = ResearchSourceRecord(
        run_id=research_run.record_id,
        url="https://example.com/rejected",
        title="Rejected source",
        status=ResearchReviewStatus.REJECTED,
        failure_reason="Duplicate reporting without primary data.",
    )
    state_service.save_research_source(accepted_source)
    state_service.save_research_source(rejected_source)

    evidence = ResearchEvidenceRecord(
        run_id=research_run.record_id,
        fact_text="Reserve capacity increased by 12 percent.",
        source_ids=[accepted_source.record_id],
        status=ResearchReviewStatus.ACCEPTED,
        evidence_kind="numeric_fact",
        numeric_value="12",
        numeric_unit="percent",
        quote_text="Reserve capacity increased by 12 percent.",
    )
    state_service.save_research_evidence(evidence)

    restored_run = state_service.load_research_run(research_run.record_id)
    restored_evidence = state_service.load_research_evidence(evidence.record_id)
    accepted_sources = state_service.list_research_sources(
        run_id=research_run.record_id,
        status=ResearchReviewStatus.ACCEPTED,
    )
    rejected_sources = state_service.list_research_sources(
        run_id=research_run.record_id,
        status=ResearchReviewStatus.REJECTED,
    )
    accepted_evidence = state_service.list_research_evidence(
        run_id=research_run.record_id,
        status=ResearchReviewStatus.ACCEPTED,
        source_id=accepted_source.record_id,
    )

    assert restored_run.source_ids == [
        accepted_source.record_id,
        rejected_source.record_id,
    ]
    assert restored_run.evidence_ids == [evidence.record_id]
    assert restored_evidence.quote_text
    assert restored_evidence.numeric_unit == "percent"
    assert [item.record_id for item in accepted_sources] == [
        accepted_source.record_id,
    ]
    assert [item.record_id for item in rejected_sources] == [
        rejected_source.record_id,
    ]
    assert [item.record_id for item in accepted_evidence] == [
        evidence.record_id,
    ]


def test_project_state_service_persists_research_brief_artifacts(tmp_path):
    """Research brief ledgers should persist alongside markdown exports."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)

    brief = ResearchBriefRecord(
        run_id="run-1",
        title="Research Brief: Grid Resilience",
        executive_summary="Coverage is 0.75 and confidence is 0.80.",
        supported_findings=["Reserve capacity increased by 12 percent."],
        open_questions=["How durable is the increase beyond 2026?"],
        weak_evidence_ids=["evidence-2"],
        coverage_score=0.75,
        confidence_score=0.8,
    )
    markdown_path = state_service.write_research_brief_markdown(
        brief.record_id,
        "# Research Brief\n",
    )
    brief.artifact_paths = [
        f".airunner/research/briefs/{brief.record_id}.json",
        markdown_path,
    ]
    state_service.save_research_brief(brief)

    restored = state_service.load_research_brief(brief.record_id)
    listed = state_service.list_research_briefs("run-1")

    assert restored.title == "Research Brief: Grid Resilience"
    assert restored.artifact_paths[1].endswith(".md")
    assert [item.record_id for item in listed] == [brief.record_id]


def test_project_state_service_persists_meeting_ledgers(tmp_path):
    """Meeting runs, items, and deliverables should persist separately."""
    project_service = AirunnerProjectService(str(tmp_path / "demo-project"))
    project_service.initialize(project_name="Demo Project")
    state_service = AirunnerProjectStateService(project_service)

    meeting_run = MeetingRunRecord(
        title="Weekly sync",
        raw_input="Alice: We ship Friday.",
        normalized_input="Alice: We ship Friday.",
        participants=["Alice", "Bob"],
    )
    state_service.save_meeting_run(meeting_run)
    decision = MeetingItemRecord(
        run_id=meeting_run.record_id,
        item_kind="decision",
        summary="Ship on Friday.",
        source_excerpt="Alice: We ship Friday.",
        status=MeetingItemStatus.CONFIRMED,
        speaker="Alice",
    )
    action_item = MeetingItemRecord(
        run_id=meeting_run.record_id,
        item_kind="action_item",
        summary="Bob confirms release checklist.",
        source_excerpt="Bob: I will confirm the release checklist.",
        status=MeetingItemStatus.TENTATIVE,
        owner="Bob",
        due_date="2026-05-06",
    )
    state_service.save_meeting_item(decision)
    state_service.save_meeting_item(action_item)

    markdown_path = state_service.write_meeting_artifact_markdown(
        "meeting-pack.md",
        "# Meeting Pack\n",
    )
    deliverable = MeetingDeliverableRecord(
        run_id=meeting_run.record_id,
        title="Meeting Pack: Weekly sync",
        action_items=["- Bob confirms release checklist."],
        decision_log=["- Ship on Friday."],
        follow_up_points=["- Bob confirms release checklist."],
        unresolved_items=["- Bob confirms release checklist."],
        source_item_ids=[decision.record_id, action_item.record_id],
        artifact_paths=[
            f".airunner/meetings/packs/{meeting_run.record_id}.json",
            markdown_path,
        ],
    )
    state_service.save_meeting_deliverable(deliverable)
    review_markdown = state_service.write_meeting_review_markdown(
        "review-1",
        "# Review\n",
    )
    review = MeetingReviewRecord(
        run_id=meeting_run.record_id,
        deliverable_id=deliverable.record_id,
        reviewer_notes="Resolve the tentative action item.",
        review_status=MeetingReviewStatus.NEEDS_REVISION,
        flagged_item_ids=[action_item.record_id],
        approved_item_ids=[decision.record_id],
        artifact_paths=[
            ".airunner/meetings/reviews/review-1.json",
            review_markdown,
        ],
    )
    state_service.save_meeting_review(review)

    restored_run = state_service.load_meeting_run(meeting_run.record_id)
    listed_runs = state_service.list_meeting_runs()
    tentative_items = state_service.list_meeting_items(
        run_id=meeting_run.record_id,
        status=MeetingItemStatus.TENTATIVE,
    )
    restored_pack = state_service.load_meeting_deliverable(
        deliverable.record_id
    )
    restored_review = state_service.load_meeting_review(review.record_id)
    listed_reviews = state_service.list_meeting_reviews(
        deliverable_id=deliverable.record_id,
        status=MeetingReviewStatus.NEEDS_REVISION,
    )

    assert restored_run.item_ids == [decision.record_id, action_item.record_id]
    assert [item.record_id for item in listed_runs] == [meeting_run.record_id]
    assert [item.record_id for item in tentative_items] == [
        action_item.record_id,
    ]
    assert restored_pack.artifact_paths[1].endswith("meeting-pack.md")
    assert restored_pack.review_status is MeetingReviewStatus.NEEDS_REVISION
    assert restored_pack.review_ids == [review.record_id]
    assert restored_review.artifact_paths[1].endswith("review-1.md")
    assert [item.record_id for item in listed_reviews] == [review.record_id]