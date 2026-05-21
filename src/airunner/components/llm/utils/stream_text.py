"""Helpers for stitching streamed text fragments."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable
import re
import unicodedata


_NO_SPACE_BEFORE = frozenset(
    ".,!?;:%)]}>/\\"
)
_OPENING_CHARS = frozenset("([{</\\")
_MARKDOWN_DELIMITERS = frozenset("*_`")
_WORD_CONTINUATION = frozenset("_")
_WORD_ENDERS = frozenset(")]}\"'")
_SENTENCE_ENDERS = frozenset(".!?;:")
_SINGLE_LETTER_WORDS = frozenset({"a", "i"})
_OPENING_QUOTE_CHARS = frozenset({'"', "'", "“"})
_COMPOUND_SUFFIX_FRAGMENTS = frozenset(
    {
        "anic",
        "ative",
        "ibility",
        "cident",
        "ding",
        "ful",
        "ical",
        "ically",
        "like",
        "loss",
        "ment",
        "mystery",
        "ness",
        "olic",
        "pective",
        "ship",
        "tion",
    }
)
_COMMON_WORDS = frozenset(
    {
        "a",
        "about",
        "after",
        "again",
        "according",
        "all",
        "an",
        "and",
        "any",
        "appears",
        "are",
        "as",
        "at",
        "based",
        "be",
        "been",
        "between",
        "bible",
        "book",
        "but",
        "by",
        "can",
        "car",
        "character",
        "characters",
        "city",
        "cold",
        "collection",
        "dead",
        "death",
        "document",
        "distinct",
        "divided",
        "dreamlike",
        "for",
        "front",
        "from",
        "graveyard",
        "green",
        "had",
        "haunted",
        "has",
        "have",
        "he",
        "help",
        "her",
        "here",
        "him",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "know",
        "la",
        "let",
        "living",
        "lunatics",
        "maximus",
        "me",
        "melancholic",
        "memory",
        "more",
        "mystery",
        "narrator",
        "night",
        "noir",
        "no",
        "not",
        "now",
        "of",
        "on",
        "one",
        "or",
        "our",
        "out",
        "photograph",
        "realms",
        "results",
        "sat",
        "search",
        "seem",
        "seems",
        "set",
        "she",
        "someone",
        "story",
        "summary",
        "supernatural",
        "satanic",
        "tale",
        "that",
        "the",
        "their",
        "them",
        "themes",
        "there",
        "they",
        "this",
        "to",
        "too",
        "two",
        "up",
        "was",
        "warm",
        "we",
        "what",
        "when",
        "where",
        "which",
        "whimsical",
        "who",
        "why",
        "will",
        "with",
        "world",
        "worlds",
        "wonder",
        "would",
        "you",
        "your",
        "years",
        "anton",
    }
)
_WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def _is_space_separated_symbol(char: str) -> bool:
    """Return True when one symbol should behave like a token."""
    if not char:
        return False
    if char in _NO_SPACE_BEFORE or char in _OPENING_CHARS:
        return False
    return unicodedata.category(char) == "So"


@lru_cache(maxsize=1)
def _load_known_words() -> frozenset[str]:
    """Return built-in words for chunk-boundary heuristics."""
    return _COMMON_WORDS


def _leading_word(chunk: str) -> str:
    """Return the alphabetic word fragment at one chunk start."""
    match = _WORD_PATTERN.match(chunk)
    return match.group(0) if match else ""


def _trailing_word(existing: str) -> str:
    """Return the alphabetic word fragment at one chunk end."""
    matches = list(_WORD_PATTERN.finditer(existing))
    return matches[-1].group(0) if matches else ""


def _is_known_word(word: str) -> bool:
    """Return whether one alphabetic token looks like a full word."""
    return word.isalpha() and word.lower() in _load_known_words()


def _looks_like_compound_suffix_fragment(fragment: str) -> bool:
    """Return whether one fragment looks like a split-word suffix."""
    lowered = str(fragment or "").lower()
    if lowered in _COMPOUND_SUFFIX_FRAGMENTS:
        return True
    return len(lowered) >= 4 and any(
        lowered.endswith(suffix)
        for suffix in ("like", "olic", "anic", "ment", "ness", "tion")
    )


def _ends_with_opening_quote(existing: str) -> bool:
    """Return whether the current buffer ends with an opening quote."""
    if not existing:
        return False
    if existing[-1] not in _OPENING_QUOTE_CHARS:
        return False
    if len(existing) == 1:
        return True
    prev_char = existing[-2]
    return prev_char.isspace() or prev_char in _OPENING_CHARS


def _should_strip_leading_space(existing: str, stripped: str) -> bool:
    """Return whether one leading space looks like a split-word artifact."""
    left = _trailing_word(existing)
    right = _leading_word(stripped)
    if not left or not right:
        return False
    if _ends_with_opening_quote(existing):
        return True
    if _is_known_word(left + right):
        return True
    if _is_known_word(left) or _is_known_word(right):
        return False
    if _looks_like_compound_suffix_fragment(right):
        return True
    return len(left) <= 3 and len(right) >= 4


def _needs_plain_word_boundary(existing: str, chunk: str) -> bool:
    """Return whether adjacent alphabetic chunks need a spacer."""
    left = _trailing_word(existing)
    right = _leading_word(chunk)
    if not left or not right:
        return False
    if len(left) == 1 or len(right) == 1:
        if _is_known_word(left + right):
            return False
        left_is_single_word = (
            left.lower() in _SINGLE_LETTER_WORDS
            and _is_known_word(right)
            and (left.islower() or left == "I")
        )
        right_is_single_word = (
            right.lower() in _SINGLE_LETTER_WORDS
            and _is_known_word(left)
            and right.islower()
        )
        return left_is_single_word or right_is_single_word
    if _is_known_word(left + right):
        return False
    if _is_known_word(left) and _is_known_word(right):
        return True
    if _is_known_word(right) and len(left) >= 4:
        return True
    if _is_known_word(left) and len(right) >= 4:
        return True
    return len(left) >= 5 and len(right) >= 4


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
    next_is_word = next_char.isalnum() or next_char in _WORD_CONTINUATION
    prev_is_symbol = _is_space_separated_symbol(prev)
    next_is_symbol = _is_space_separated_symbol(next_char)

    if prev_is_word and next_char in _MARKDOWN_DELIMITERS:
        return True
    if prev in _MARKDOWN_DELIMITERS and next_is_word:
        return existing.count(prev) % 2 == 0
    if _ends_with_opening_quote(existing):
        return False

    if prev_is_word and next_is_word:
        return _needs_plain_word_boundary(existing, chunk)

    if prev == ',' and (next_char.isalpha() or next_is_symbol):
        return True
    if prev in _SENTENCE_ENDERS and (next_is_word or next_is_symbol):
        return True
    if prev in _WORD_ENDERS and (next_is_word or next_is_symbol):
        return True
    if prev_is_symbol and (next_is_word or next_is_symbol):
        return True
    if next_is_symbol and prev_is_word:
        return True
    return False


def prepare_stream_chunk(existing: str, chunk: str) -> str:
    """Prefix one chunk with a spacer when the boundary needs it."""
    if not chunk:
        return ""
    stripped_split_word = False
    if chunk[:1].isspace():
        stripped = chunk.lstrip()
        if (
            stripped
            and existing
            and (
                existing[-1].isalpha()
                or _ends_with_opening_quote(existing)
            )
            and stripped[0].islower()
            and _should_strip_leading_space(existing, stripped)
        ):
            chunk = stripped
            stripped_split_word = True
    if stripped_split_word:
        return chunk
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