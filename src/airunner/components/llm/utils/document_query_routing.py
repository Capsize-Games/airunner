"""Request-time routing for loaded-document questions."""

from __future__ import annotations

from dataclasses import dataclass
import re

from airunner.components.llm.config.document_tasks import (
    DEFAULT_DOCUMENT_TASK,
    DOCUMENT_SURFACE_PATTERNS,
    DOCUMENT_TASK_CONFIGS,
    DocumentTaskConfig,
)


@dataclass(frozen=True)
class DocumentQueryRoute:
    """One request-time plan for a document question."""

    intent: str
    force_tool: str
    answer_mode: str


def _normalize_prompt(prompt: str) -> str:
    """Return a lowercase prompt with normalized whitespace."""
    return " ".join(str(prompt or "").lower().split())


def _matches_any(prompt: str, patterns: tuple[str, ...]) -> bool:
    """Return whether the prompt matches any routing pattern."""
    return any(re.search(pattern, prompt) for pattern in patterns)


def _mentions_document_surface(prompt: str) -> bool:
    """Return whether the prompt clearly refers to one document surface."""
    return _matches_any(prompt, DOCUMENT_SURFACE_PATTERNS)


def _matches_document_task(
    prompt: str,
    config: DocumentTaskConfig,
    assume_document_mode: bool,
) -> bool:
    """Return whether the prompt matches one configured document task."""
    if config.direct_patterns and _matches_any(prompt, config.direct_patterns):
        return True
    if not config.contextual_patterns:
        return False
    if not _matches_any(prompt, config.contextual_patterns):
        return False
    return assume_document_mode or _mentions_document_surface(prompt)


def route_document_query(
    prompt: str,
    *,
    assume_document_mode: bool = False,
) -> DocumentQueryRoute | None:
    """Return the request-time route for one document question."""
    normalized = _normalize_prompt(prompt)
    if not normalized:
        return None
    for config in DOCUMENT_TASK_CONFIGS:
        if _matches_document_task(normalized, config, assume_document_mode):
            return DocumentQueryRoute(
                intent=config.intent,
                force_tool=config.force_tool,
                answer_mode=config.answer_mode,
            )
    if assume_document_mode:
        return DocumentQueryRoute(
            intent=DEFAULT_DOCUMENT_TASK.intent,
            force_tool=DEFAULT_DOCUMENT_TASK.force_tool,
            answer_mode=DEFAULT_DOCUMENT_TASK.answer_mode,
        )
    return None