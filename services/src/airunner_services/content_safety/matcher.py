"""Generic content-safety matcher primitives (hash-based; no plaintext terms).

This module is the input-side layer of the content-safety feature. The
repository never stores the prohibited policy terms. Instead it stores only
SHA-256 hashes of normalized token n-grams; the real hash set is generated
out of band by ``scripts/build_policy_terms.py`` and is never committed.

Normalization (deterministic, obfuscation-resistant)
----------------------------------------------------
:func:`normalize_tokens` applies, in order: Unicode NFKC, case-fold, NFKD
plus combining-mark removal (drops diacritics), replacement of every
non-alphanumeric character with a space, tokenization on whitespace, and
collapsing of any run of three or more identical characters down to two.

Matching additionally hashes a second "de-obfuscated" variant of each token
in which common digit/symbol substitutions are folded back to letters
(e.g. ``4`` -> ``a``, ``0`` -> ``o``), and 1-, 2- and 3-gram windows of the
normalized token sequence (both space-joined and delimiter-free).

Fail behavior (deliberately fail-open on missing data)
------------------------------------------------------
So the application stays usable before the owner generates a real policy
set, a missing, empty, or all-malformed policy data file does NOT raise:
:func:`~airunner_services.content_safety.policy_data.is_available` returns
``False``, a single content-free warning is logged, and :func:`check_text`
/ :func:`check_prompt_fields` report the input as allowed. Corrupt lines are
skipped rather than raising. The enforced, fail-closed output-side layer is
a separate concern handled elsewhere.

No-disclosure guarantee
-----------------------
Nothing here logs, returns, or otherwise surfaces the checked text or any
matched term. Only booleans, counts, field names and generic reason codes
leave these functions.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass

from .policy_data import load_policy_hashes

REASON_ALLOWED = "ok"
REASON_PROHIBITED = "prohibited_content"

NORMALIZATION_VERSION = "v1"
NGRAM_MIN = 1
NGRAM_MAX = 3

# Fixed, word-free homoglyph/leet fold table. Safe to commit: it contains no
# policy term, only single-character substitutions.
_OBFUSCATION_FOLD = str.maketrans(
    {
        "0": "o",
        "1": "l",
        "2": "z",
        "3": "e",
        "4": "a",
        "5": "s",
        "6": "g",
        "7": "t",
        "8": "b",
        "9": "g",
        "@": "a",
        "$": "s",
        "!": "i",
        "|": "l",
    }
)

_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")
_REPEAT_RUN_RE = re.compile(r"(.)\1{2,}")


@dataclass(frozen=True)
class ContentSafetyResult:
    """Outcome of checking one or more named text fields.

    ``reason`` is always a generic code; it never contains field text or a
    matched term.
    """

    allowed: bool
    reason: str
    field: str | None

    @classmethod
    def allowed_result(cls) -> "ContentSafetyResult":
        """Return an allowed outcome."""
        return cls(allowed=True, reason=REASON_ALLOWED, field=None)

    @classmethod
    def blocked_result(cls, field: str, reason: str) -> "ContentSafetyResult":
        """Return a blocked outcome for ``field`` with a generic ``reason``."""
        return cls(allowed=False, reason=reason, field=field)


def _collapse_repeats(value: str) -> str:
    """Collapse any run of three or more identical characters down to two."""
    return _REPEAT_RUN_RE.sub(r"\1\1", value)


def normalize_tokens(text: str) -> list[str]:
    """Normalize ``text`` into deterministic, obfuscation-resistant tokens.

    Returns an empty list for non-string or empty input. The transformation
    is stable: the same input always yields the same token list.
    """
    if not isinstance(text, str) or not text:
        return []
    value = unicodedata.normalize("NFKC", text).casefold()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = _NON_ALNUM_RE.sub(" ", value)
    tokens: list[str] = []
    for raw in value.split():
        collapsed = _collapse_repeats(raw)
        if collapsed:
            tokens.append(collapsed)
    return tokens


def _fold_token(token: str) -> str:
    """Return the de-obfuscated (digit/symbol folded) variant of ``token``."""
    return _collapse_repeats(token.translate(_OBFUSCATION_FOLD))


def hash_token(token: str) -> str:
    """Return the lowercase hex SHA-256 digest of ``token`` (UTF-8)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ngram_windows(tokens: list[str], size: int) -> Iterator[list[str]]:
    for index in range(len(tokens) - size + 1):
        yield [tokens[offset] for offset in range(index, index + size)]


def candidate_hashes(text: str) -> set[str]:
    """Return every SHA-256 hash that ``text`` could match against.

    The set covers 1-, 2- and 3-gram windows of the normalized tokens (both
    space-joined and delimiter-free) and each individual token, for both the
    raw normalized form and the de-obfuscated fold variant. Ordering is not
    significant.
    """
    tokens = normalize_tokens(text)
    if not tokens:
        return set()
    sequences = (tokens, [_fold_token(token) for token in tokens])
    hashes: set[str] = set()
    for sequence in sequences:
        for size in range(NGRAM_MIN, NGRAM_MAX + 1):
            for window in _ngram_windows(sequence, size):
                hashes.add(hash_token(" ".join(window)))
                if size > 1:
                    hashes.add(hash_token("".join(window)))
        for token in sequence:
            hashes.add(hash_token(token))
    return hashes


def check_text(text: str) -> bool:
    """Return ``True`` when ``text`` passes (i.e. no policy match).

    Returns ``True`` when no policy data is loaded, so the application stays
    usable until the owner generates a real policy set.
    """
    if not isinstance(text, str) or not text:
        return True
    hashes = load_policy_hashes()
    if not hashes:
        return True
    return not any(
        candidate in hashes for candidate in candidate_hashes(text)
    )


def check_prompt_fields(**fields: str) -> ContentSafetyResult:
    """Check named text fields and report the first blocking one.

    ``None`` and empty fields are skipped. The returned reason is generic and
    never echoes field text or a matched term; only the offending field name
    is reported.
    """
    for field, value in fields.items():
        if not isinstance(value, str) or not value:
            continue
        if not check_text(value):
            return ContentSafetyResult.blocked_result(field, REASON_PROHIBITED)
    return ContentSafetyResult.allowed_result()


__all__ = [
    "ContentSafetyResult",
    "NGRAM_MAX",
    "NGRAM_MIN",
    "NORMALIZATION_VERSION",
    "REASON_ALLOWED",
    "REASON_PROHIBITED",
    "candidate_hashes",
    "check_prompt_fields",
    "check_text",
    "hash_token",
    "normalize_tokens",
]
