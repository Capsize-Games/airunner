#!/usr/bin/env python3
"""Validate AIRunner UwUChat tenant schema is migrated and usable.

Usage:
  python -m airunner.scripts.validate_uwuchat_tenant --user-id <uuid>

Notes:
- Requires AIRunner to be configured for Postgres schema tenancy.
- Reads DB URL from `AIRUNNER_DATABASE_URL` / `AIRUNNER_DB_URL` (via airunner.settings).
- Does not write data; it only checks that expected tables exist.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import create_engine, text
from sqlalchemy import pool

from airunner.components.data.tenant import tenant_schema_for_user_id
from airunner.components.data.session_manager import _tenant_db_url
from airunner.settings import AIRUNNER_DB_URL
from airunner.utils.crypto.data_encryption import get_keyring


REQUIRED_TABLES = {
    "uwuchat_chat_sessions",
    "uwuchat_messages",
    "uwuchat_media",
    "uwuchat_profile",
    "alembic_version",
}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate a tenant schema contains UwUChat tables")
    p.add_argument("--user-id", required=True, help="UwUChat user id (UUID) used as tenant key")
    p.add_argument(
        "--database-url",
        default=None,
        help="Override DB URL (otherwise uses AIRunner settings/env)",
    )
    return p.parse_args(argv)


def _is_postgres(url: str) -> bool:
    u = (url or "").lower()
    return u.startswith("postgresql") or u.startswith("postgres")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv or sys.argv[1:]))

    base_url = (args.database_url or AIRUNNER_DB_URL or "").strip()
    if not base_url:
        print("ERROR: No database URL configured (AIRUNNER_DB_URL / AIRUNNER_DATABASE_URL)")
        return 2

    if not _is_postgres(base_url):
        print(f"ERROR: Expected Postgres URL, got: {base_url.split(':', 1)[0]}")
        return 2

    tenant_schema = tenant_schema_for_user_id(args.user_id)
    tenant_url = _tenant_db_url(base_url, tenant_schema)

    keyring = get_keyring(required=False)
    if keyring is None:
        print("WARNING: AIRUNNER_DATA_ENCRYPTION_KEYS is not set (encrypted user data writes should fail)")

    engine = create_engine(tenant_url, poolclass=pool.NullPool)

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                """
            )
        ).fetchall()

        tables = {r[0] for r in rows}

        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            print(f"ERROR: Missing tables in schema '{tenant_schema}': {', '.join(missing)}")
            print("Hint: ensure a request has initialized this tenant or run migrations via setup_database().")
            return 1

        alembic_version = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()

    print(f"OK: tenant schema '{tenant_schema}' has required UwUChat tables")
    print(f"alembic_version={alembic_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
