"""Document splitting and summary-sampling helpers for RAG tools."""

import re
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._shared import (
    FRONT_MATTER_HEADINGS,
)


def looks_like_generic_heading(line: str) -> bool:
    """Return whether one line resembles a plain chapter heading."""
    normalized = " ".join(str(line or "").split())
    if not normalized or normalized != normalized.upper():
        return False
    if any(mark in normalized for mark in ('"', ",", ".", "!", "?")):
        return False

    words = normalized.split()
    if len(words) < 2 or len(words) > 10:
        return False

    alpha_chars = [char for char in normalized if char.isalpha()]
    return len(alpha_chars) >= 8


def extract_document_structure_headings(text: str) -> list[str]:
    """Extract major structure headings from one source document."""
    pattern = re.compile(
        r"^(INTRODUCTION|PROLOGUE|THE BOOK OF [A-Z][A-Z' -]+|"
        r"BOOK OF [A-Z][A-Z' -]+|PART [A-Z0-9IVXLC]+(?:[: .-].*)?|"
        r"CHAPTER [A-Z0-9IVXLC]+(?:[: .-].*)?)$"
    )
    headings: list[str] = []
    seen: set[str] = set()
    for raw_line in str(text or "").splitlines():
        line = " ".join(raw_line.strip().split())
        if not line or len(line) > 120:
            continue
        if not pattern.fullmatch(line) and not looks_like_generic_heading(
            line
        ):
            continue
        if line in seen:
            continue
        seen.add(line)
        headings.append(line)
    return headings


def append_section(
    sections: list[tuple[str, str]],
    title: str,
    lines: list[str],
) -> None:
    """Append one non-empty section body to the section list."""
    body = "\n".join(lines).strip()
    if not body:
        return
    sections.append((title or "Opening context", body))


def split_document_sections(text: str) -> list[tuple[str, str]]:
    """Split one document into heading-oriented sections when possible."""
    headings = extract_document_structure_headings(text)
    if not headings:
        return []

    sections: list[tuple[str, str]] = []
    heading_set = set(headings)
    current_title = ""
    current_lines: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            if current_lines and current_lines[-1] != "":
                current_lines.append("")
            continue
        if line in heading_set:
            append_section(sections, current_title, current_lines)
            current_title = line
            current_lines = []
            continue
        current_lines.append(line)

    append_section(sections, current_title, current_lines)
    return sections


def split_document_paragraphs(
    text: str,
    *,
    min_words: int = 12,
) -> list[str]:
    """Return substantive paragraphs from one extracted document."""
    paragraphs: list[str] = []
    for paragraph in re.split(r"\n\s*\n", str(text or "")):
        cleaned = " ".join(paragraph.split())
        if len(cleaned.split()) >= min_words:
            paragraphs.append(cleaned)
    return paragraphs


def normalize_section_title(title: str) -> str:
    """Return one normalized section title for summary heuristics."""
    return " ".join(str(title or "").upper().split())


def select_evenly_spaced_items(items: list[Any], limit: int) -> list[Any]:
    """Return up to limit items distributed across the input list."""
    if len(items) <= limit:
        return list(items)
    if limit <= 1:
        return [items[0]]

    last_index = len(items) - 1
    return [
        items[int(index * last_index / (limit - 1))] for index in range(limit)
    ]


def select_section_summary_paragraphs(
    title: str,
    paragraphs: list[str],
) -> list[str]:
    """Return paragraph samples that best represent one section."""
    if not paragraphs:
        return []

    normalized_title = normalize_section_title(title)
    if normalized_title in FRONT_MATTER_HEADINGS and len(paragraphs) > 1:
        return [paragraphs[len(paragraphs) // 2]]

    limit = 1 if normalized_title in FRONT_MATTER_HEADINGS else 2
    return select_evenly_spaced_items(paragraphs, min(limit, len(paragraphs)))


def build_section_summary_units(
    sections: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Return paragraph-level units distributed across document sections."""
    units: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for title, body in sections:
        paragraphs = split_document_paragraphs(body)
        if not paragraphs:
            cleaned = " ".join(str(body or "").split())
            if cleaned:
                paragraphs = [cleaned]
        for paragraph in select_section_summary_paragraphs(title, paragraphs):
            key = (title, paragraph)
            if key in seen:
                continue
            seen.add(key)
            units.append(key)
    return units


def truncate_summary_evidence(text: str, limit: int = 420) -> str:
    """Trim one evidence snippet to a readable prompt-sized span."""
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned

    snippet = cleaned[:limit].rsplit(" ", 1)[0].strip()
    sentence_breaks = [snippet.rfind(marker) for marker in (". ", "! ", "? ")]
    best_break = max(sentence_breaks)
    if best_break >= 120:
        snippet = snippet[: best_break + 1].strip()
    if snippet.endswith((".", "!", "?")):
        return snippet
    return snippet + "..."


def build_summary_evidence_text(
    title: str,
    body: str,
    position: int,
) -> str:
    """Format one section or region as summary evidence text."""
    normalized_title = normalize_section_title(title)
    if title and normalized_title in FRONT_MATTER_HEADINGS:
        prefix = f"Front matter ({title}). "
    elif title:
        prefix = f"Section: {title}. "
    else:
        prefix = f"Document region {position}. "
    return prefix + truncate_summary_evidence(body)


__all__ = [
    "build_section_summary_units",
    "build_summary_evidence_text",
    "extract_document_structure_headings",
    "normalize_section_title",
    "select_evenly_spaced_items",
    "split_document_paragraphs",
    "split_document_sections",
    "truncate_summary_evidence",
]
