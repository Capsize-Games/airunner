"""Workflow tools for meeting ingestion and deliverable generation."""

from typing import Any

from airunner.components.agents.runtime import MeetingDeliverableRecord
from airunner.components.agents.runtime import MeetingItemRecord
from airunner.components.agents.runtime import MeetingItemStatus
from airunner.components.agents.runtime import MeetingRunRecord
from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)
from airunner.components.document_editor.project.airunner_active_project import (
    get_active_project_path,
)
from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _resolve_meeting_project_path(project_path: str = "") -> str:
    """Return the initialized project path used for meeting tools."""
    resolved = project_path or get_active_project_path() or ""
    if not resolved:
        raise ValueError(
            "Meeting tools require an active or explicit project path."
        )
    project_service = AirunnerProjectService(resolved)
    if not project_service.exists():
        raise ValueError("Meeting tools require an initialized project.")
    return project_service.project_path


def _meeting_state_service(
    project_path: str = "",
) -> AirunnerProjectStateService:
    """Return the project-state service used by meeting tools."""
    project_service = AirunnerProjectService(
        _resolve_meeting_project_path(project_path)
    )
    return AirunnerProjectStateService(project_service)


def _normalize_meeting_input(text: str) -> str:
    """Return a deterministic normalized meeting transcript or notes."""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    cleaned = [line for line in lines if line]
    return "\n".join(cleaned)


def _meeting_item_payload(item: MeetingItemRecord) -> dict[str, Any]:
    """Return a compact tool payload for one meeting item."""
    return {
        "item_id": item.record_id,
        "run_id": item.run_id,
        "item_kind": item.item_kind,
        "summary": item.summary,
        "status": item.status.value,
        "confidence": item.confidence,
        "speaker": item.speaker,
        "owner": item.owner,
        "due_date": item.due_date,
        "source_excerpt": item.source_excerpt,
    }


def _item_line(item: MeetingItemRecord) -> str:
    """Render one meeting item for markdown output."""
    bits = [item.summary]
    if item.owner:
        bits.append(f"owner: {item.owner}")
    if item.due_date:
        bits.append(f"due: {item.due_date}")
    if item.status != MeetingItemStatus.CONFIRMED:
        bits.append(f"status: {item.status.value}")
    return "- " + " | ".join(bits)


def _deliverable_markdown(
    deliverable: MeetingDeliverableRecord,
) -> dict[str, str]:
    """Render stable markdown artifacts for one meeting deliverable pack."""
    pack_lines = [
        f"# {deliverable.title}",
        "",
        "## Action Items",
        "",
    ]
    action_items = deliverable.action_items or ["- No action items recorded."]
    pack_lines.extend(action_items)
    pack_lines.extend(["", "## Decision Log", ""])
    decisions = deliverable.decision_log or ["- No decisions recorded."]
    pack_lines.extend(decisions)
    pack_lines.extend(["", "## Follow-Up Draft", ""])
    follow_up = deliverable.follow_up_points or ["- No follow-up points recorded."]
    pack_lines.extend(follow_up)
    pack_lines.extend(["", "## Unresolved Items", ""])
    unresolved = deliverable.unresolved_items or ["- No unresolved items recorded."]
    pack_lines.extend(unresolved)

    email_lines = [
        f"# Follow-Up Draft: {deliverable.title}",
        "",
        "Thanks everyone. Here are the confirmed follow-ups from the meeting:",
        "",
    ]
    email_lines.extend(deliverable.follow_up_points or ["- None recorded."])

    decision_lines = [f"# Decision Log: {deliverable.title}", ""]
    decision_lines.extend(deliverable.decision_log or ["- None recorded."])

    return {
        "pack.md": "\n".join(pack_lines),
        "follow_up.md": "\n".join(email_lines),
        "decisions.md": "\n".join(decision_lines),
    }


@tool(
    name="start_meeting_run",
    category=ToolCategory.WORKFLOW,
    description=(
        "Normalize meeting transcript or notes into a durable meeting run "
        "before extracting structured decisions, tasks, and questions."
    ),
)
def start_meeting_run(
    title: str,
    source_text: str,
    source_kind: str = "transcript",
    participants: list[str] | None = None,
    project_path: str = "",
) -> dict[str, Any]:
    """Create one normalized meeting run inside the active project."""
    state_service = _meeting_state_service(project_path)
    meeting_run = MeetingRunRecord(
        title=title,
        raw_input=source_text,
        normalized_input=_normalize_meeting_input(source_text),
        source_kind=source_kind,
        participants=list(participants or []),
    )
    state_service.save_meeting_run(meeting_run)
    return {
        "meeting_run_id": meeting_run.record_id,
        "title": meeting_run.title,
        "source_kind": meeting_run.source_kind,
        "normalized_input": meeting_run.normalized_input,
    }


@tool(
    name="record_meeting_item",
    category=ToolCategory.WORKFLOW,
    description=(
        "Persist one structured meeting extraction item such as a decision, "
        "action item, risk, deadline, or open question."
    ),
)
def record_meeting_item(
    meeting_run_id: str,
    item_kind: str,
    summary: str,
    source_excerpt: str,
    status: str = "unresolved",
    confidence: str = "medium",
    speaker: str = "",
    owner: str = "",
    due_date: str = "",
    note: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Persist one extracted meeting item for later deliverable generation."""
    state_service = _meeting_state_service(project_path)
    item = MeetingItemRecord(
        run_id=meeting_run_id,
        item_kind=item_kind,
        summary=summary,
        source_excerpt=source_excerpt,
        status=MeetingItemStatus(status),
        confidence=confidence,
        speaker=speaker,
        owner=owner,
        due_date=due_date,
        metadata={"note": note} if note else {},
    )
    state_service.save_meeting_item(item)
    return _meeting_item_payload(item)


@tool(
    name="search_meeting_items",
    category=ToolCategory.WORKFLOW,
    description=(
        "Search structured meeting items by text, kind, or status without "
        "reprocessing the source transcript."
    ),
)
def search_meeting_items(
    query: str,
    meeting_run_id: str = "",
    item_kind: str = "",
    status: str = "",
    limit: int = 10,
    project_path: str = "",
) -> dict[str, Any]:
    """Return structured meeting items that match one query."""
    state_service = _meeting_state_service(project_path)
    items = state_service.list_meeting_items(
        run_id=meeting_run_id or None,
        item_kind=item_kind or None,
        status=MeetingItemStatus(status) if status else None,
    )
    terms = [term for term in query.lower().split() if term.strip()]
    matches: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        blob = "\n".join(
            [
                item.item_kind,
                item.summary,
                item.source_excerpt,
                item.speaker,
                item.owner,
                item.due_date,
                item.status.value,
            ]
        ).lower()
        score = sum(1 for term in terms if term in blob) if terms else 1
        if score <= 0:
            continue
        matches.append((score, _meeting_item_payload(item)))
    matches.sort(key=lambda item: item[0], reverse=True)
    return {
        "query": query,
        "match_count": len(matches[:limit]),
        "matches": [payload for _score, payload in matches[:limit]],
    }


@tool(
    name="generate_meeting_deliverable_pack",
    category=ToolCategory.WORKFLOW,
    description=(
        "Generate action-item, decision-log, and follow-up deliverables "
        "from structured meeting state without rerunning extraction."
    ),
)
def generate_meeting_deliverable_pack(
    meeting_run_id: str,
    title: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Create one user-facing deliverable pack from structured items."""
    state_service = _meeting_state_service(project_path)
    meeting_run = state_service.load_meeting_run(meeting_run_id)
    items = state_service.list_meeting_items(run_id=meeting_run_id)
    decisions = [
        _item_line(item)
        for item in items
        if item.item_kind == "decision"
        and item.status is MeetingItemStatus.CONFIRMED
    ]
    action_items = [
        _item_line(item)
        for item in items
        if item.item_kind == "action_item"
    ]
    unresolved_items = [
        _item_line(item)
        for item in items
        if item.status in {
            MeetingItemStatus.TENTATIVE,
            MeetingItemStatus.CONFLICTING,
            MeetingItemStatus.UNRESOLVED,
        }
    ]
    follow_up_points = decisions + action_items
    pack_title = title or f"Meeting Pack: {meeting_run.title}"
    deliverable = MeetingDeliverableRecord(
        run_id=meeting_run_id,
        title=pack_title,
        action_items=action_items,
        decision_log=decisions,
        follow_up_points=follow_up_points,
        unresolved_items=unresolved_items,
        metadata={
            "meeting_title": meeting_run.title,
            "confirmed_decisions": len(decisions),
            "action_item_count": len(action_items),
            "unresolved_count": len(unresolved_items),
        },
    )
    artifacts = _deliverable_markdown(deliverable)
    artifact_paths: list[str] = []
    for suffix, content in artifacts.items():
        file_name = f"{deliverable.record_id}_{suffix}"
        artifact_paths.append(
            state_service.write_meeting_artifact_markdown(file_name, content)
        )
    deliverable.artifact_paths = [
        state_service._meeting_deliverable_path(deliverable.record_id),
        *artifact_paths,
    ]
    state_service.save_meeting_deliverable(deliverable)
    return {
        "deliverable_id": deliverable.record_id,
        "meeting_run_id": meeting_run_id,
        "title": deliverable.title,
        "action_item_count": len(deliverable.action_items),
        "decision_count": len(deliverable.decision_log),
        "unresolved_count": len(deliverable.unresolved_items),
        "artifact_paths": list(deliverable.artifact_paths),
    }