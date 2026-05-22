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
    summary_focus: str | None = None


_PREMISE_SUMMARY_PATTERNS = (
    r"\bwhat(?:'s| is)\s+(?:this|the)\s+"
    r"(?:book|novel|story|document|file)\s+about\b",
    r"\bwhat\s+is\s+the\s+(?:book|novel|story|document|file)\s+about\b",
    r"\btell\s+me\s+about\s+(?:this|the)\s+"
    r"(?:book|novel|story|document|file)\b",
    r"\bwhat\s+is\s+the\s+premise(?:\s+and\s+theme[s]?)?\s+of\s+"
    r"(?:this|the)\s+(?:book|novel|story|document|file)\b",
    r"\bwhat\s+are\s+the\s+premise\s+and\s+theme[s]?\s+of\s+"
    r"(?:this|the)\s+(?:book|novel|story|document|file)\b",
    r"\bdescribe\s+the\s+premise(?:\s+and\s+theme[s]?)?\s+of\s+"
    r"(?:this|the)\s+(?:book|novel|story|document|file)\b",
    r"\b(?:synopsis|plot)\s+of\s+(?:this|the)\s+"
    r"(?:book|novel|story|document|file)\b",
    r"\bwhat\s+happens\s+in\s+(?:this|the)\s+"
    r"(?:book|novel|story|document|file)\b",
)

_PREMISE_SUMMARY_KEYWORDS = (
    "premise",
    "plot",
    "synopsis",
)

_OVERVIEW_SUMMARY_KEYWORDS = (
    "summary",
    "summarize",
    "overview",
    "main idea",
    "main topic",
    "theme",
    "themes",
)

_SUMMARY_REQUEST_VERBS = (
    "describe",
    "explain",
    "give",
    "outline",
    "provide",
    "tell",
    "walk me through",
    "what",
)


def _normalize_prompt(prompt: str) -> str:
    """Return a lowercase prompt with normalized whitespace."""
    return " ".join(str(prompt or "").lower().split())


def _matches_any(prompt: str, patterns: tuple[str, ...]) -> bool:
    """Return whether the prompt matches any routing pattern."""
    return any(re.search(pattern, prompt) for pattern in patterns)


def _mentions_document_surface(prompt: str) -> bool:
    """Return whether the prompt clearly refers to one document surface."""
    return _matches_any(prompt, DOCUMENT_SURFACE_PATTERNS)


def infer_document_summary_focus(
    prompt: str,
    *,
    assume_document_mode: bool = False,
) -> str | None:
    """Return one request-time summary subtype for a document prompt."""
    normalized = _normalize_prompt(prompt)
    if not normalized:
        return None

    in_document_mode = assume_document_mode or _mentions_document_surface(
        normalized
    )
    if not in_document_mode:
        return None

    if _matches_any(normalized, _PREMISE_SUMMARY_PATTERNS):
        return "premise"

    has_summary_verb = any(
        verb in normalized for verb in _SUMMARY_REQUEST_VERBS
    )
    if has_summary_verb and any(
        keyword in normalized for keyword in _PREMISE_SUMMARY_KEYWORDS
    ):
        return "premise"

    if any(keyword in normalized for keyword in _OVERVIEW_SUMMARY_KEYWORDS):
        return "overview"

    return None


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
                summary_focus=(
                    infer_document_summary_focus(
                        normalized,
                        assume_document_mode=assume_document_mode,
                    )
                    if config.intent == "summary"
                    else None
                ),
            )

    summary_focus = infer_document_summary_focus(
        normalized,
        assume_document_mode=assume_document_mode,
    )
    if summary_focus is not None:
        return DocumentQueryRoute(
            intent="summary",
            force_tool="rag_search",
            answer_mode="synthesized",
            summary_focus=summary_focus,
        )

    if assume_document_mode:
        return DocumentQueryRoute(
            intent=DEFAULT_DOCUMENT_TASK.intent,
            force_tool=DEFAULT_DOCUMENT_TASK.force_tool,
            answer_mode=DEFAULT_DOCUMENT_TASK.answer_mode,
            summary_focus=None,
        )
    return None