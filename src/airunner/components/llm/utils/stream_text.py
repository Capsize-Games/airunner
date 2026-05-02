"""Helpers for stitching streamed text fragments."""

from __future__ import annotations

from typing import Iterable


_NO_SPACE_BEFORE = frozenset(
    ".,!?;:%)]}>/\\"
)
_OPENING_CHARS = frozenset("([{</\\")
_WORD_CONTINUATION = frozenset("_")
_WORD_ENDERS = frozenset(")]}\"'")


def needs_stream_space(existing: str, chunk: str) -> bool:
    """Return True when one chunk boundary needs a spacer."""
    if not existing or not chunk:
        return False
    prev = existing[-1]
    next_char = chunk[0]
    if prev.isspace() or next_char.isspace():
        return False
    if next_char in _NO_SPACE_BEFORE or prev in _OPENING_CHARS:
        return False
    prev_is_word = prev.isalnum() or prev in _WORD_CONTINUATION
    prev_is_word = prev_is_word or prev in _WORD_ENDERS
    next_is_word = next_char.isalnum() or next_char in _WORD_CONTINUATION
    return prev_is_word and next_is_word


def prepare_stream_chunk(existing: str, chunk: str) -> str:
    """Prefix one chunk with a spacer when the boundary needs it."""
    if not chunk:
        return ""
    if needs_stream_space(existing, chunk):
        return f" {chunk}"
    return chunk


def append_stream_text(existing: str, chunk: str) -> str:
    """Append one streamed chunk using boundary-aware spacing."""
    prepared = prepare_stream_chunk(existing, chunk)
    if not prepared:
        return existing
    return existing + prepared


def combine_stream_chunks(chunks: Iterable[str]) -> str:
    """Combine streamed chunks into one readable string."""
    combined = ""
    for chunk in chunks:
        combined = append_stream_text(combined, chunk)
    return combined