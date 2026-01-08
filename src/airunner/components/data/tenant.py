from __future__ import annotations

import re
import os
from contextvars import ContextVar, Token


_tenant_key: ContextVar[str | None] = ContextVar("airunner_tenant_key", default=None)
_schema_prefix: ContextVar[str] = ContextVar(
    "airunner_tenant_schema_prefix", default="tenant_"
)


def set_tenant_key(value: str | None) -> Token[str | None]:
    cleaned = (value or "").strip()
    return _tenant_key.set(cleaned or None)


def reset_tenant_key(token: Token[str | None]) -> None:
    _tenant_key.reset(token)


def get_tenant_key() -> str | None:
    return _tenant_key.get()


def get_tenant_schema_prefix() -> str:
    value = (_schema_prefix.get() or "").strip()
    if value:
        return value
    env = (os.environ.get("AIRUNNER_TENANT_SCHEMA_PREFIX") or "").strip()
    return env or "tenant_"


def set_tenant_schema_prefix(prefix: str) -> Token[str]:
    cleaned = (prefix or "").strip()
    return _schema_prefix.set(cleaned or "tenant_")


def reset_tenant_schema_prefix(token: Token[str]) -> None:
    _schema_prefix.reset(token)


_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def tenant_schema_for_key(key: str | None) -> str:
    """Convert a tenant key into a Postgres schema name.

    Constraints:
    - Keep names deterministic and safe.
    - Avoid quoting needs (lowercase + underscores only).
    """

    raw = (key or "").strip().lower()
    if _UUID_RE.match(raw):
        raw = raw.replace("-", "")
        return f"{get_tenant_schema_prefix()}{raw}"

    # Fallback: best-effort sanitize.
    raw = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    if not raw:
        raw = "anonymous"
    return f"{get_tenant_schema_prefix()}{raw}"
