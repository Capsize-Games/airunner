"""Public interface for the content-safety input matcher.

This package implements a small, hash-based input gate for a set of
prohibited policy terms. The repository never stores the terms themselves:
only SHA-256 hashes of normalized token n-grams, generated out of band by
``scripts/build_policy_terms.py``.

See :mod:`airunner_services.content_safety.matcher` for the normalization
and matching rules and :mod:`airunner_services.content_safety.policy_data`
for data loading and availability semantics.

Nothing in this package logs or returns the checked text or any matched
term; only booleans, counts, field names and generic reason codes are
surfaced.
"""

from __future__ import annotations

from .config import (
    CONTENT_POLICY_DISABLED,
    CONTENT_POLICY_ENFORCE,
    CONTENT_POLICY_MODE_ENV_VAR,
    ContentPolicyConfigurationError,
    ContentPolicyMode,
    content_policy_is_enforced,
    resolve_content_policy_mode,
)
from .matcher import (
    NORMALIZATION_VERSION,
    REASON_ALLOWED,
    REASON_PROHIBITED,
    ContentSafetyResult,
    candidate_hashes,
    check_prompt_fields,
    check_text,
    hash_token,
    normalize_tokens,
)
from .policy_data import (
    POLICY_DATA_ENV_VAR,
    POLICY_DATA_FILENAME,
    is_available,
    load_policy_hashes,
    reset_cache,
)
from .semantic import (
    SEMANTIC_ENV_VAR,
    SEMANTIC_TIMEOUT_SECONDS,
    REASON_AMBIGUOUS,
    REASON_BLOCKED,
    REASON_DISABLED,
    REASON_ERROR,
    REASON_TIMEOUT,
    REASON_UNAVAILABLE,
    SemanticVerdict,
    build_judge_instruction,
    evaluate_fields_semantic,
    get_judge,
    make_llm_judge,
    parse_judge_response,
    semantic_enabled,
    set_judge,
)

__all__ = [
    "CONTENT_POLICY_DISABLED",
    "CONTENT_POLICY_ENFORCE",
    "CONTENT_POLICY_MODE_ENV_VAR",
    "ContentPolicyConfigurationError",
    "ContentSafetyResult",
    "ContentPolicyMode",
    "NORMALIZATION_VERSION",
    "POLICY_DATA_ENV_VAR",
    "POLICY_DATA_FILENAME",
    "REASON_ALLOWED",
    "REASON_AMBIGUOUS",
    "REASON_BLOCKED",
    "REASON_DISABLED",
    "REASON_ERROR",
    "REASON_PROHIBITED",
    "REASON_TIMEOUT",
    "REASON_UNAVAILABLE",
    "SEMANTIC_ENV_VAR",
    "SEMANTIC_TIMEOUT_SECONDS",
    "SemanticVerdict",
    "build_judge_instruction",
    "content_policy_is_enforced",
    "candidate_hashes",
    "check_prompt_fields",
    "check_text",
    "evaluate_fields_semantic",
    "get_judge",
    "hash_token",
    "is_available",
    "load_policy_hashes",
    "make_llm_judge",
    "normalize_tokens",
    "parse_judge_response",
    "reset_cache",
    "resolve_content_policy_mode",
    "semantic_enabled",
    "set_judge",
]
