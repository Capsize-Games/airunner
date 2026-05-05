"""Tests for meeting artifact tools that open editor documents."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.components.llm.core.tool_registry import ToolRegistry
from airunner.components.llm.tools.meeting_document_tools import (
    open_meeting_deliverable_artifact,
    open_meeting_review_artifact,
)
from airunner.components.llm.tools.meeting_tools import (
    generate_meeting_deliverable_pack,
    record_meeting_item,
    review_meeting_deliverable_pack,
    start_meeting_run,
)
from airunner.enums import SignalCode


def test_meeting_document_tools_are_registered():
    """Meeting document tools should be available to workflow agents."""
    for tool_name in (
        "open_meeting_deliverable_artifact",
        "open_meeting_review_artifact",
    ):
        assert tool_name in ToolRegistry._tools
        assert ToolRegistry._tools[tool_name].category == ToolCategory.WORKFLOW


def test_open_meeting_deliverable_artifact_emits_editor_signal(tmp_path):
    """Opening a meeting pack should emit a locked-document signal."""
    project_path = tmp_path / "meeting-project"
    service = AirunnerProjectService(str(project_path))
    service.initialize(project_name="Meeting Project")
    api = SimpleNamespace(emit_signal=Mock())

    started = start_meeting_run(
        title="Weekly sync",
        source_text="Alice: We ship Friday.",
        project_path=str(project_path),
    )
    record_meeting_item(
        meeting_run_id=started["meeting_run_id"],
        item_kind="decision",
        summary="Ship on Friday.",
        source_excerpt="Alice: We ship Friday.",
        status="confirmed",
        project_path=str(project_path),
    )
    pack = generate_meeting_deliverable_pack(
        meeting_run_id=started["meeting_run_id"],
        project_path=str(project_path),
    )

    result = open_meeting_deliverable_artifact(
        deliverable_id=pack["deliverable_id"],
        artifact_kind="pack",
        project_path=str(project_path),
        api=api,
    )

    api.emit_signal.assert_called_once()
    args = api.emit_signal.call_args.args
    assert args[0] is SignalCode.OPEN_MEETING_DOCUMENT
    assert args[1]["locked"] is True
    assert result["title"] == "Meeting Pack: Weekly sync"
    assert result["path"].endswith("_pack.md")


def test_open_meeting_review_artifact_emits_editor_signal(tmp_path):
    """Opening a meeting review should emit the locked-document signal."""
    project_path = tmp_path / "meeting-project"
    service = AirunnerProjectService(str(project_path))
    service.initialize(project_name="Meeting Project")
    api = SimpleNamespace(emit_signal=Mock())

    started = start_meeting_run(
        title="Weekly sync",
        source_text="Alice: We ship Friday.\nBob: I will confirm the checklist.",
        project_path=str(project_path),
    )
    record_meeting_item(
        meeting_run_id=started["meeting_run_id"],
        item_kind="decision",
        summary="Ship on Friday.",
        source_excerpt="Alice: We ship Friday.",
        status="confirmed",
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
    review = review_meeting_deliverable_pack(
        meeting_run_id=started["meeting_run_id"],
        deliverable_id=pack["deliverable_id"],
        reviewer_notes="Confirmed the owner.",
        approve=True,
        corrections=[
            {
                "item_id": action_item["item_id"],
                "summary": "Bob confirms release checklist.",
                "status": "confirmed",
                "confidence": "high",
                "owner": "Bob",
            }
        ],
        project_path=str(project_path),
    )

    result = open_meeting_review_artifact(
        deliverable_id=pack["deliverable_id"],
        review_id=review["review_id"],
        project_path=str(project_path),
        api=api,
    )

    api.emit_signal.assert_called_once()
    args = api.emit_signal.call_args.args
    assert args[0] is SignalCode.OPEN_MEETING_DOCUMENT
    assert args[1]["title"] == "Review: Meeting Pack: Weekly sync"
    assert result["review_id"] == review["review_id"]
    assert result["path"].endswith(".md")