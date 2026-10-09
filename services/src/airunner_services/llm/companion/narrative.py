"""Bounded, sanitized narrative blending (release issue B09).

Pure blend data and logic: source tracking, memory-injection
sanitation, and explicit char/token budgets. The background-job
half (reviewed-summary reads, version-guarded writes) lives in
``memory_blend.py``; rolling compression lives in ``compression.py``.

No model, network, GPU, or database I/O here; blending through a
``BlendFn`` is injected by the caller.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from .contracts import SessionId
    from .jobs import JobContext
    from .repository import NarrativeRecord

# Explicit budgets: the stored narrative never exceeds either bound,
# whatever the blend function returns.
MAX_NARRATIVE_CHARS = 4000
MAX_NARRATIVE_TOKENS = 1000

# Rough tokenizer-free estimate both writers share (compression.py
# reuses it so the two budgets stay comparable).
_CHARS_PER_TOKEN = 4

# Instruction-injection markers, matched per line, case-insensitively.
# Neutral prompt-shaped lines ("she told him to sit") never match:
# every pattern anchors on an imperative addressed at the reader.
_INSTRUCTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^\s*ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"^\s*disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"^\s*override\s+(all\s+)?(previous|prior)\s+instructions",
        r"^\s*forget\s+(everything|all)(\s+you\s+know)?\s*$",
        r"^\s*you\s+are\s+now\s+",
        r"^\s*new\s+instructions\s*:",
        r"^\s*system\s*:",
        r"^\s*\[system\]",
    )
)


class NarrativeSource(BaseModel):
    """One blend input with a stable id for source tracking."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    kind: str  # "previous", "episodic", or "fact"
    text: str


class NarrativeBlend(BaseModel):
    """One blended narrative with its provenance and size."""

    model_config = ConfigDict(extra="forbid")

    content: str
    sources: List[str] = []
    dropped: List[str] = []
    char_count: int = 0
    token_estimate: int = 0


# May raise retryable CompanionError when inference is unavailable.
BlendFn = Callable[["JobContext", List[NarrativeSource]], NarrativeBlend]


def estimate_tokens(text: str) -> int:
    """Rough token count used for every B09 budget check."""
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def is_instruction_line(line: str) -> bool:
    """True when one line looks like an injected instruction."""
    return any(p.match(line) is not None for p in _INSTRUCTION_PATTERNS)


def sanitize_memory_text(text: str) -> str:
    """Drop instruction-like lines; keep every other line verbatim."""
    kept = [ln for ln in text.splitlines() if not is_instruction_line(ln)]
    return "\n".join(kept).strip()


def fit_to_budget(text: str, max_chars: int, max_tokens: int) -> str:
    """Truncate to the tighter of a char and a token budget."""
    cap = min(max_chars, max_tokens * _CHARS_PER_TOKEN)
    if len(text) <= cap:
        return text
    return text[:cap].rstrip()


def blend_narrative(
    sources: List[NarrativeSource],
    *,
    max_chars: int = MAX_NARRATIVE_CHARS,
    max_tokens: int = MAX_NARRATIVE_TOKENS,
) -> NarrativeBlend:
    """Deterministic bounded merge; the previous narrative survives.

    Sources sanitize first (an input that sanitizes to nothing is
    dropped as an instruction-only payload), then join in order. Over
    budget, oldest non-previous sources drop first; the previous
    narrative is never dropped, only truncated as a last resort.
    """
    segments, dropped = _sanitized_segments(sources)
    while _over_budget(segments, max_chars, max_tokens):
        if not _drop_oldest_addition(segments, dropped):
            break
    return _assemble(segments, dropped, max_chars, max_tokens)


def _sanitized_segments(
    sources: List[NarrativeSource],
) -> Tuple[List[Tuple[NarrativeSource, str]], List[str]]:
    """Sanitize inputs; instruction-only ones land in dropped."""
    segments: List[Tuple[NarrativeSource, str]] = []
    dropped: List[str] = []
    for source in sources:
        clean = sanitize_memory_text(source.text)
        if clean:
            segments.append((source, clean))
        else:
            dropped.append(source.source_id)
    return segments, dropped


def _assemble(
    segments: List[Tuple[NarrativeSource, str]],
    dropped: List[str],
    max_chars: int,
    max_tokens: int,
) -> NarrativeBlend:
    """Join survivors within budget and record provenance."""
    content = fit_to_budget(
        "\n".join(text for _, text in segments), max_chars, max_tokens
    )
    return NarrativeBlend(
        content=content,
        sources=[src.source_id for src, _ in segments],
        dropped=dropped,
        char_count=len(content),
        token_estimate=estimate_tokens(content),
    )


def _over_budget(
    segments: List[Tuple[NarrativeSource, str]],
    max_chars: int,
    max_tokens: int,
) -> bool:
    """True when the joined segments exceed either budget."""
    joined = "\n".join(text for _, text in segments)
    return len(joined) > min(max_chars, max_tokens * _CHARS_PER_TOKEN)


def _drop_oldest_addition(
    segments: List[Tuple[NarrativeSource, str]], dropped: List[str]
) -> bool:
    """Drop the earliest non-previous segment; False if none left."""
    for index, (source, _) in enumerate(segments):
        if source.kind != "previous":
            dropped.append(source.source_id)
            del segments[index]
            return True
    return False


def blend_sources(
    current: Optional[NarrativeRecord],
    session_id: SessionId,
    summary: str,
) -> List[NarrativeSource]:
    """Previous narrative first, then the reviewed episodic text."""
    sources: List[NarrativeSource] = []
    previous = _previous_source(current)
    if previous is not None:
        sources.append(previous)
    sources.append(
        NarrativeSource(
            source_id=f"episodic:{session_id}",
            kind="episodic",
            text=summary,
        )
    )
    return sources


def _previous_source(
    current: Optional[NarrativeRecord],
) -> Optional[NarrativeSource]:
    """The stored narrative as a blend source, if one has content."""
    if current is None or not current.content.strip():
        return None
    return NarrativeSource(
        source_id=f"narrative:v{current.version}",
        kind="previous",
        text=current.content,
    )


__all__ = [
    "BlendFn",
    "MAX_NARRATIVE_CHARS",
    "MAX_NARRATIVE_TOKENS",
    "NarrativeBlend",
    "NarrativeSource",
    "blend_narrative",
    "blend_sources",
    "estimate_tokens",
    "fit_to_budget",
    "is_instruction_line",
    "sanitize_memory_text",
]
