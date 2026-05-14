"""Helpers for keeping sensitive values out of default logs."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from collections.abc import Mapping
from typing import Any


_URL_PATTERN = re.compile(r"https?://[^\s\"'<>),;]+")
_PATH_PATTERN = re.compile(
    r"(?P<path>(?:~|/)[^\s\"'<>),;]+(?:/[^\s\"'<>),;]+)+)"
)


def summarize_text(text: str | None, *, label: str = "text") -> str:
    """Return one length-only summary for one text payload."""
    if not text:
        return f"{label}_chars=0"
    return f"{label}_chars={len(text)}"


def summarize_mapping_keys(
    value: Any,
    *,
    label: str = "data",
    max_keys: int = 8,
) -> str:
    """Return one key-only summary for one mapping payload."""
    if not isinstance(value, Mapping):
        return f"{label}_type={type(value).__name__}"

    keys = sorted(str(key) for key in value.keys())
    preview = ", ".join(keys[:max_keys])
    if len(keys) > max_keys:
        preview = f"{preview}, ..."
    return f"{label}_keys=[{preview}]"


def fingerprint_value(
    value: str | None,
    *,
    label: str = "value",
) -> str:
    """Return one stable fingerprint for one string without logging it."""
    if not value:
        return f"{label}_present=false"

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{label}_hash={digest}"


def sanitize_log_text(text: str) -> str:
    """Redact URLs and filesystem paths from one log string."""
    sanitized = _URL_PATTERN.sub(
        lambda match: fingerprint_value(match.group(0), label="url"),
        text,
    )
    return _PATH_PATTERN.sub(
        lambda match: fingerprint_value(match.group("path"), label="path"),
        sanitized,
    )


def sanitize_log_value(value: Any) -> Any:
    """Sanitize one log value while preserving basic formatting."""
    if isinstance(value, Mapping):
        return summarize_mapping_keys(value)

    if isinstance(value, os.PathLike):
        return fingerprint_value(os.fspath(value), label="path")

    if isinstance(value, bytes):
        return f"bytes_len={len(value)}"

    if isinstance(value, str):
        return sanitize_log_text(value)

    return value


def sanitize_log_args(args: Any) -> Any:
    """Sanitize one logging args payload."""
    if isinstance(args, Mapping):
        return {key: sanitize_log_value(value) for key, value in args.items()}

    if isinstance(args, tuple):
        return tuple(sanitize_log_value(value) for value in args)

    return sanitize_log_value(args)


class LogHygieneFilter(logging.Filter):
    """Filter log records so common sensitive values do not leak by default."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, Mapping):
            record.msg = summarize_mapping_keys(record.msg, label="message")
            record.args = ()
            return True

        if isinstance(record.msg, os.PathLike):
            record.msg = fingerprint_value(
                os.fspath(record.msg),
                label="path",
            )
            record.args = ()
            return True

        if isinstance(record.msg, str):
            record.msg = sanitize_log_text(record.msg)
            if record.args:
                record.args = sanitize_log_args(record.args)
            return True

        record.msg = sanitize_log_text(str(record.msg))
        if record.args:
            record.args = sanitize_log_args(record.args)
        return True