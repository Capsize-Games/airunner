"""Backward-compatible re-export of the shared log-hygiene helpers.

The canonical implementation lives in :mod:`airunner_common.logging_utils`.
This module is retained only so the legacy import path keeps resolving; it
contains no duplicated logic (issue #2050).
"""

from __future__ import annotations

from airunner_common.logging_utils import (
    LogHygieneFilter,
    fingerprint_value,
    sanitize_log_args,
    sanitize_log_text,
    sanitize_log_value,
    summarize_mapping_keys,
    summarize_text,
)

__all__ = [
    "LogHygieneFilter",
    "fingerprint_value",
    "sanitize_log_args",
    "sanitize_log_text",
    "sanitize_log_value",
    "summarize_mapping_keys",
    "summarize_text",
]
