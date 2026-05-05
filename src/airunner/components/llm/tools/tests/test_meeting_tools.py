"""Focused tests for meeting ingestion and deliverable workflow tools."""

from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import AirunnerProjectStateService
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.components.llm.core.tool_registry import ToolRegistry
from airunner.components.llm.tools.meeting_tools import (
    get_meeting_review_queue,
    generate_meeting_deliverable_pack,
    record_meeting_item,
    review_meeting_deliverable_pack,
    search_meeting_items,
    start_meeting_run,
)


def test_meeting_tools_are_registered():
    """Meeting workflow tools should be available to agents."""
    for tool_name in (
        "start_meeting_run",
        "record_meeting_item",
        "search_meeting_items",
        "generate_meeting_deliverable_pack",
        "get_meeting_review_queue",
        "review_meeting_deliverable_pack",
    ):
        assert tool_name in ToolRegistry._tools
        assert ToolRegistry._tools[tool_name].category == ToolCategory.WORKFLOW


def test_meeting_tools_persist_structured_items(tmp_path):
    """Meeting tools should normalize input and persist extracted items."""
    project_path = tmp_path / "meeting-project"
    project_service = AirunnerProjectService(str(project_path))
    project_service.initialize(project_name="Meeting Project")
    state_service = AirunnerProjectStateService(project_service)

    started = start_meeting_run(
        title="Weekly sync",
        source_text="Alice:   We ship Friday.\n\nBob: I will confirm the checklist.",
        participants=["Alice", "Bob"],
        project_path=str(project_path),
    )
    item = record_meeting_item(
        meeting_run_id=started["meeting_run_id"],
        item_kind="decision",
        summary="Ship on Friday.",
        source_excerpt="Alice: We ship Friday.",
        status="confirmed",
        speaker="Alice",
        project_path=str(project_path),
    )

    restored_run = state_service.load_meeting_run(started["meeting_run_id"])
    restored_item = state_service.load_meeting_item(item["item_id"])

    assert started["normalized_input"] == (
        "Alice: We ship Friday.\nBob: I will confirm the checklist."
    )
    assert restored_run.participants == ["Alice", "Bob"]
    assert restored_item.summary == "Ship on Friday."


def test_generate_meeting_deliverable_pack_exports_artifacts(tmp_path):
    """Meeting deliverables should be generated from structured state."""
    project_path = tmp_path / "meeting-project"
    project_service = AirunnerProjectService(str(project_path))
    project_service.initialize(project_name="Meeting Project")
    state_service = AirunnerProjectStateService(project_service)

    started = start_meeting_run(
        title="Weekly sync",
        source_text="Alice: We ship Friday.\nBob: I will confirm the checklist.",
        participants=["Alice", "Bob"],
        project_path=str(project_path),
    )
    record_meeting_item(
        meeting_run_id=started["meeting_run_id"],
        item_kind="decision",
        summary="Ship on Friday.",
        source_excerpt="Alice: We ship Friday.",
        status="confirmed",
        speaker="Alice",
        project_path=str(project_path),
    )
    record_meeting_item(
        meeting_run_id=started["meeting_run_id"],
        item_kind="action_item",
        summary="Bob confirms release checklist.",
        source_excerpt="Bob: I will confirm the checklist.",
        status="tentative",
        owner="Bob",
        due_date="2026-05-06",
        project_path=str(project_path),
    )

    results = search_meeting_items(
        query="release checklist",
        meeting_run_id=started["meeting_run_id"],
        project_path=str(project_path),
    )
    pack = generate_meeting_deliverable_pack(
        meeting_run_id=started["meeting_run_id"],
        project_path=str(project_path),
    )
    restored_pack = state_service.load_meeting_deliverable(
        pack["deliverable_id"]
    )
    markdown = project_service.read_file(restored_pack.artifact_paths[1])

    assert results["match_count"] == 1
    assert pack["decision_count"] == 1
    assert pack["action_item_count"] == 1
    assert pack["unresolved_count"] == 1
    assert markdown.startswith("# Meeting Pack: Weekly sync")


def test_review_meeting_deliverable_pack_persists_approval_state(tmp_path):
    """Meeting review flow should persist corrections and approval state."""
    project_path = tmp_path / "meeting-project"
    project_service = AirunnerProjectService(str(project_path))
    project_service.initialize(project_name="Meeting Project")
    state_service = AirunnerProjectStateService(project_service)

    started = start_meeting_run(
        title="Weekly sync",
        source_text="Alice: We ship Friday.\nBob: I will confirm the checklist.",
        participants=["Alice", "Bob"],
        project_path=str(project_path),
    )
    decision = record_meeting_item(
        meeting_run_id=started["meeting_run_id"],
        item_kind="decision",
        summary="Ship on Friday.",
        source_excerpt="Alice: We ship Friday.",
        status="confirmed",
        confidence="high",
        speaker="Alice",
        project_path=str(project_path),
    )
    action_item = record_meeting_item(
        meeting_run_id=started["meeting_run_id"],
        item_kind="action_item",
        summary="Confirm release checklist.",
        source_excerpt="Bob: I will confirm the checklist.",
        status="tentative",
        confidence="low",
        owner="Bob",
        project_path=str(project_path),
    )
    pack = generate_meeting_deliverable_pack(
        meeting_run_id=started["meeting_run_id"],
        project_path=str(project_path),
    )

    queue = get_meeting_review_queue(
        meeting_run_id=started["meeting_run_id"],
        deliverable_id=pack["deliverable_id"],
        project_path=str(project_path),
    )
    review = review_meeting_deliverable_pack(
        meeting_run_id=started["meeting_run_id"],
        deliverable_id=pack["deliverable_id"],
        reviewer_notes="Confirmed the action item owner and commitment.",
        approve=True,
        corrections=[
            {
                "item_id": action_item["item_id"],
                "summary": "Bob confirms release checklist.",
                "status": "confirmed",
                "confidence": "high",
                "owner": "Bob",
                "note": "Validated against Bob's closing statement.",
            }
        ],
        project_path=str(project_path),
    )
    restored_pack = state_service.load_meeting_deliverable(
        pack["deliverable_id"]
    )
    restored_review = state_service.load_meeting_review(review["review_id"])
    corrected_item = state_service.load_meeting_item(action_item["item_id"])
    markdown = project_service.read_file(restored_review.artifact_paths[1])

    assert decision["item_id"] in restored_pack.approved_item_ids
    assert queue["flagged_count"] == 1
    assert queue["flagged_items"][0]["source_excerpt"] == (
        "Bob: I will confirm the checklist."
    )
    assert review["review_status"] == "approved"
    assert restored_pack.review_status.value == "approved"
    assert sorted(restored_review.approved_item_ids) == sorted(
        [decision["item_id"], action_item["item_id"]]
    )
    assert corrected_item.status.value == "confirmed"
    assert markdown.startswith("# Review: Meeting Pack: Weekly sync")