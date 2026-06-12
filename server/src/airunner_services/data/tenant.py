"""Service-owned tenant context helpers."""

from __future__ import annotations

import contextlib
import os
import re
from contextvars import ContextVar, Token

_tenant_key: ContextVar[str | None] = ContextVar(
    "airunner_tenant_key",
    default=None,
)
_schema_prefix: ContextVar[str] = ContextVar(
    "airunner_tenant_schema_prefix",
    default="tenant_",
)


def set_tenant_key(value: str | None) -> Token[str | None]:
    """Store one tenant key in context-local state."""
    cleaned = (value or "").strip()
    return _tenant_key.set(cleaned or None)


def reset_tenant_key(token: Token[str | None]) -> None:
    """Restore the previous tenant key token."""
    _tenant_key.reset(token)


def get_tenant_key() -> str | None:
    """Return the current tenant key if one is active."""
    return _tenant_key.get()


@contextlib.contextmanager
def tenant_scope(key: str | None):
    """Activate one tenant key for the duration of a block.

    Always restores the previous key on exit — including when ``key`` is
    ``None`` — so the contextvar cannot leak across reused threads (e.g.
    the long-lived ``LLMGenerateWorker`` queue thread that processes work
    for many tenants in sequence).
    """
    token = set_tenant_key(key)
    try:
        yield
    finally:
        reset_tenant_key(token)


def get_tenant_schema_prefix() -> str:
    """Return the configured tenant schema prefix."""
    value = (_schema_prefix.get() or "").strip()
    if value:
        return value
    env = (os.environ.get("AIRUNNER_TENANT_SCHEMA_PREFIX") or "").strip()
    return env or "tenant_"


def set_tenant_schema_prefix(prefix: str) -> Token[str]:
    """Store one schema prefix in context-local state."""
    cleaned = (prefix or "").strip()
    return _schema_prefix.set(cleaned or "tenant_")


def reset_tenant_schema_prefix(token: Token[str]) -> None:
    """Restore the previous tenant schema prefix token."""
    _schema_prefix.reset(token)


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def tenant_schema_for_key(key: str | None) -> str:
    """Convert one tenant key into a safe deterministic schema name."""
    raw = (key or "").strip().lower()
    if _UUID_RE.match(raw):
        raw = raw.replace("-", "")
        return f"{get_tenant_schema_prefix()}{raw}"

    raw = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    if not raw:
        raw = "anonymous"
    return f"{get_tenant_schema_prefix()}{raw}"


def tenant_key_from_schema(schema: str | None) -> str | None:
    """Recover the raw tenant key from a fully-qualified schema name.

    This is the inverse of :func:`tenant_schema_for_key` for the purpose
    of feeding :func:`set_tenant_key`, which expects the *raw* key (it
    re-applies the prefix internally).  Callers that hold a materialised
    schema name (e.g. decoded from a JWT or read from a column) must use
    this before calling ``set_tenant_key`` to avoid double-prefixing.
    """
    raw = (schema or "").strip()
    if not raw:
        return None
    prefix = get_tenant_schema_prefix()
    if prefix and raw.startswith(prefix):
        raw = raw[len(prefix) :]
    return raw or None


__all__ = [
    "get_tenant_key",
    "get_tenant_schema_prefix",
    "reset_tenant_key",
    "reset_tenant_schema_prefix",
    "set_tenant_key",
    "set_tenant_schema_prefix",
    "tenant_scope",
    "tenant_schema_for_key",
    "tenant_key_from_schema",
]
