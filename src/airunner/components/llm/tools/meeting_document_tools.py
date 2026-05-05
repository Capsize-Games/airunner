"""Document-editor bridge tools for meeting workflow artifacts."""

from typing import Any

from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)
from airunner.components.document_editor.project.airunner_active_project import (
    get_active_project_path,
)
from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _resolve_project_path(project_path: str = "") -> str:
    """Return the initialized project path for meeting artifacts."""
    resolved = project_path or get_active_project_path() or ""
    if not resolved:
        raise ValueError(
            "Meeting artifact tools require an active or explicit project."
        )
    project_service = AirunnerProjectService(resolved)
    if not project_service.exists():
        raise ValueError("Meeting artifact tools require a project.")
    return project_service.project_path


def _meeting_services(
    project_path: str = "",
) -> tuple[AirunnerProjectService, AirunnerProjectStateService]:
    """Return the project and state services for meeting artifacts."""
    project_service = AirunnerProjectService(_resolve_project_path(project_path))
    return project_service, AirunnerProjectStateService(project_service)


def _latest_deliverable(state_service, meeting_run_id: str = ""):
    """Return the requested or latest meeting deliverable pack."""
    deliverables = state_service.list_meeting_deliverables(
        run_id=meeting_run_id or None
    )
    if not deliverables:
        raise ValueError("No meeting deliverable pack is available yet.")
    return max(deliverables, key=lambda item: item.created_at)


def _resolve_deliverable(state_service, meeting_run_id: str, deliverable_id: str):
    """Return one deliverable pack by id or latest run output."""
    if deliverable_id:
        return state_service.load_meeting_deliverable(deliverable_id)
    return _latest_deliverable(state_service, meeting_run_id)


def _latest_review(state_service, deliverable_id: str):
    """Return the latest review pass for one deliverable pack."""
    reviews = state_service.list_meeting_reviews(deliverable_id=deliverable_id)
    if not reviews:
        raise ValueError("No meeting review artifact is available yet.")
    return max(reviews, key=lambda item: item.created_at)


def _resolve_review(state_service, deliverable_id: str, review_id: str):
    """Return one review pass by id or latest deliverable review."""
    if review_id:
        return state_service.load_meeting_review(review_id)
    return _latest_review(state_service, deliverable_id)


def _deliverable_rel_path(deliverable, artifact_kind: str) -> str:
    """Return one deliverable artifact path by kind."""
    suffixes = {
        "pack": "_pack.md",
        "follow_up": "_follow_up.md",
        "decisions": "_decisions.md",
    }
    suffix = suffixes.get(artifact_kind, "_pack.md")
    for rel_path in deliverable.artifact_paths:
        if rel_path.endswith(suffix):
            return rel_path
    raise ValueError(f"No meeting artifact found for kind: {artifact_kind}")


def _deliverable_title(title: str, artifact_kind: str) -> str:
    """Return the editor title for one deliverable artifact."""
    titles = {
        "pack": title,
        "follow_up": f"Follow-Up: {title}",
        "decisions": f"Decisions: {title}",
    }
    return titles.get(artifact_kind, title)


def _open_document(api: Any, path: str, title: str) -> None:
    """Emit one document-open signal for the editor surface."""
    api.emit_signal(
        SignalCode.OPEN_MEETING_DOCUMENT,
        {"path": path, "locked": True, "title": title},
    )


@tool(
    name="open_meeting_deliverable_artifact",
    category=ToolCategory.WORKFLOW,
    description=(
        "Open a generated meeting pack artifact in the document editor as a "
        "locked tab so the user can inspect it."
    ),
    return_direct=False,
    requires_api=True,
)
def open_meeting_deliverable_artifact(
    meeting_run_id: str = "",
    deliverable_id: str = "",
    artifact_kind: str = "pack",
    project_path: str = "",
    api: Any = None,
) -> dict[str, str]:
    """Open one meeting deliverable artifact in the document editor."""
    if api is None:
        return {"error": "API not available"}
    project_service, state_service = _meeting_services(project_path)
    deliverable = _resolve_deliverable(
        state_service,
        meeting_run_id,
        deliverable_id,
    )
    rel_path = _deliverable_rel_path(deliverable, artifact_kind)
    abs_path = project_service.resolve_path(rel_path)
    title = _deliverable_title(deliverable.title, artifact_kind)
    _open_document(api, abs_path, title)
    return {"path": abs_path, "title": title, "artifact_kind": artifact_kind}


@tool(
    name="open_meeting_review_artifact",
    category=ToolCategory.WORKFLOW,
    description=(
        "Open the latest persisted meeting review artifact in the document "
        "editor as a locked tab for inspection."
    ),
    return_direct=False,
    requires_api=True,
)
def open_meeting_review_artifact(
    meeting_run_id: str = "",
    deliverable_id: str = "",
    review_id: str = "",
    project_path: str = "",
    api: Any = None,
) -> dict[str, str]:
    """Open one meeting review artifact in the document editor."""
    if api is None:
        return {"error": "API not available"}
    project_service, state_service = _meeting_services(project_path)
    deliverable = _resolve_deliverable(
        state_service,
        meeting_run_id,
        deliverable_id,
    )
    review = _resolve_review(state_service, deliverable.record_id, review_id)
    abs_path = project_service.resolve_path(review.artifact_paths[1])
    title = f"Review: {deliverable.title}"
    _open_document(api, abs_path, title)
    return {"path": abs_path, "title": title, "review_id": review.record_id}