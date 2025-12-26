from __future__ import annotations

import re
from contextvars import ContextVar, Token


_tenant_key: ContextVar[str | None] = ContextVar("airunner_tenant_key", default=None)


def set_tenant_key(value: str | None) -> Token[str | None]:
    cleaned = (value or "").strip()
    return _tenant_key.set(cleaned or None)


def reset_tenant_key(token: Token[str | None]) -> None:
    _tenant_key.reset(token)


def get_tenant_key() -> str | None:
    return _tenant_key.get()


_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def tenant_schema_for_user_id(user_id: str | None) -> str:
    """Convert a UwUChat user id into a Postgres schema name.

    Constraints:
    - Keep names deterministic and safe.
    - Avoid quoting needs (lowercase + underscores only).
    """

    raw = (user_id or "").strip().lower()
    if _UUID_RE.match(raw):
        raw = raw.replace("-", "")
        return f"uwu_{raw}"

    # Fallback: best-effort sanitize.
    raw = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    if not raw:
        raw = "anonymous"
    return f"uwu_{raw}"
