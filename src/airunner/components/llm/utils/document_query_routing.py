"""Request-time routing for loaded-document questions."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DocumentQueryRoute:
    """One request-time plan for a document question."""

    intent: str
    force_tool: str


_DOCUMENT_SURFACE_PATTERNS = (
    r"\bdocument\b",
    r"\bfile\b",
    r"\bbook\b",
    r"\bpdf\b",
    r"\buploaded\b",
    r"\bloaded\b",
)
_IDENTITY_PATTERNS = (
    r"\bwhat(?:'s| is)\s+(?:this|the)\s+(?:document|file|book)\b",
    r"\bwhich\s+(?:document|file|book)\s+is\s+this\b",
    r"\bidentify\s+(?:this|the)\s+(?:document|file|book)\b",
    r"\bwhat\s+documents?\s+(?:are\s+)?(?:loaded|uploaded|available)\b",
)
_IDENTITY_HINT_PATTERNS = (
    r"\btitle\b",
    r"\bauthor\b",
    r"\bwho\s+wrote\b",
    r"\bfile\s+type\b",
    r"\bformat\b",
    r"\bextension\b",
)
_STRUCTURE_PATTERNS = (
    r"\btable\s+of\s+contents\b",
    r"\bchapters?\b",
    r"\bsections?\b",
    r"\boutline\b",
    r"\bdocument\s+structure\b",
)
_SUMMARY_PATTERNS = (
    r"\bsummar(?:ize|y)\b",
    r"\boverview\b",
    r"\bmain\s+(?:idea|topic|theme)\b",
    r"\bwhat\s+is\s+(?:this|the)\s+(?:document|book)\s+about\b",
)


def _normalize_prompt(prompt: str) -> str:
    """Return a lowercase prompt with normalized whitespace."""
    return " ".join(str(prompt or "").lower().split())


def _matches_any(prompt: str, patterns: tuple[str, ...]) -> bool:
    """Return whether the prompt matches any routing pattern."""
    return any(re.search(pattern, prompt) for pattern in patterns)


def _mentions_document_surface(prompt: str) -> bool:
    """Return whether the prompt clearly refers to one document surface."""
    return _matches_any(prompt, _DOCUMENT_SURFACE_PATTERNS)


def _is_structure_prompt(prompt: str, assume_document_mode: bool) -> bool:
    """Return whether the question is asking for document structure."""
    if not _matches_any(prompt, _STRUCTURE_PATTERNS):
        return False
    return assume_document_mode or _mentions_document_surface(prompt)


def _is_summary_prompt(prompt: str, assume_document_mode: bool) -> bool:
    """Return whether the question is asking for a document summary."""
    if not _matches_any(prompt, _SUMMARY_PATTERNS):
        return False
    return assume_document_mode or _mentions_document_surface(prompt)


def _is_identity_prompt(prompt: str, assume_document_mode: bool) -> bool:
    """Return whether the question is asking for document identity."""
    if _matches_any(prompt, _IDENTITY_PATTERNS):
        return True
    if not _matches_any(prompt, _IDENTITY_HINT_PATTERNS):
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
    if _is_structure_prompt(normalized, assume_document_mode):
        return DocumentQueryRoute("structure", "inspect_loaded_documents")
    if _is_summary_prompt(normalized, assume_document_mode):
        return DocumentQueryRoute("summary", "rag_search")
    if _is_identity_prompt(normalized, assume_document_mode):
        return DocumentQueryRoute("identity", "inspect_loaded_documents")
    if assume_document_mode:
        return DocumentQueryRoute("retrieval", "rag_search")
    return None