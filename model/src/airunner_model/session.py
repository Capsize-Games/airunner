"""Canonical database session management.

Provides ``session_scope()`` and engine helpers used by the real
ORM layer (``RealBaseManager``).  The api layer uses these
directly; the bridge layer wraps calls through HTTP instead.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import pool
from sqlalchemy.orm import scoped_session, sessionmaker

from airunner_model.db.engine import create_configured_engine
from airunner_model.settings import AIRUNNER_DB_URL as DEFAULT_AIRUNNER_DB_URL


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def _db_url() -> str:
    """Return the active database URL with env overrides applied lazily."""
    return os.environ.get("AIRUNNER_DATABASE_URL") or DEFAULT_AIRUNNER_DB_URL


def _tenancy_mode() -> str:
    return (
        os.environ.get("AIRUNNER_DB_TENANCY", "single") or "single"
    ).strip().lower()


def _is_postgres(url: str) -> bool:
    normalized = (url or "").lower()
    return normalized.startswith("postgresql") or normalized.startswith(
        "postgres"
    )


def _tenant_key() -> str:
    if _tenancy_mode() == "single":
        return "default"
    # Lazy import to avoid circular deps
    from airunner_model.tenant import (
        get_tenant_key,
        tenant_schema_for_key,
    )

    return tenant_schema_for_key(get_tenant_key())


def _tenant_db_url(base_url: str, tenant_schema: str) -> str:
    """Build one per-tenant database URL."""
    from sqlalchemy.engine import make_url
    from sqlalchemy.engine.url import URL

    url = make_url(base_url)
    query = dict(url.query or {})
    query["options"] = f"-csearch_path={tenant_schema}"
    new_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=url.database,
        query=query,
    )
    return new_url.render_as_string(hide_password=False)


# ---------------------------------------------------------------------------
# Engine / session globals
# ---------------------------------------------------------------------------
_engines: dict[str, object] = {}
_sessions: dict[str, scoped_session] = {}
_migrated_tenants: set[str] = set()


def _ensure_sqlite_parent_dir(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    db_path = url.replace("sqlite:///", "", 1)
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def _ensure_tenant_ready(tenant: str) -> None:
    if _tenancy_mode() == "single":
        return
    if (os.environ.get("AIRUNNER_MIGRATION_RUNNING") or "").strip() == "1":
        return

    db_url = _db_url()
    if not _is_postgres(db_url) or tenant in _migrated_tenants:
        return

    from sqlalchemy import text
    from airunner_model.setup_database import (  # noqa: PLC0415
        setup_database,
    )

    base_engine = create_configured_engine(
        db_url,
        poolclass=pool.NullPool,
    )
    with base_engine.begin() as connection:
        connection.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {tenant}")
        )

    tenant_url = _tenant_db_url(db_url, tenant)
    setup_database(db_url=tenant_url)
    _migrated_tenants.add(tenant)


def _get_engine(tenant: str):
    """Get or create one SQLAlchemy engine."""
    engine_key = tenant
    db_url = _db_url()
    if _tenancy_mode() != "single" and _is_postgres(db_url):
        engine_key = "__shared__"

    if engine_key not in _engines:
        _ensure_sqlite_parent_dir(db_url)

        pool_size = int(os.environ.get("AIRUNNER_DB_POOL_SIZE", "20"))
        max_overflow = int(
            os.environ.get("AIRUNNER_DB_MAX_OVERFLOW", "40")
        )
        pool_timeout = int(
            os.environ.get("AIRUNNER_DB_POOL_TIMEOUT", "60")
        )
        pool_recycle = int(
            os.environ.get("AIRUNNER_DB_POOL_RECYCLE", "0")
        )

        engine_kwargs = {
            "pool_pre_ping": True,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
        }
        if pool_recycle > 0:
            engine_kwargs["pool_recycle"] = pool_recycle

        _engines[engine_key] = create_configured_engine(
            db_url,
            **engine_kwargs,
        )

    return _engines[engine_key]


def _get_session(tenant: str):
    """Get or create one scoped session factory."""
    if tenant not in _sessions:
        _sessions[tenant] = scoped_session(
            sessionmaker(bind=_get_engine(tenant))
        )
    return _sessions[tenant]


def reset_engine():
    """Reset engines and sessions so later calls recreate them."""
    global _engines, _sessions, _migrated_tenants

    for session_factory in list(_sessions.values()):
        try:
            session_factory.remove()
        except Exception:
            pass
    _sessions = {}

    for engine in list(_engines.values()):
        try:
            engine.dispose()
        except Exception:
            pass
    _engines = {}
    _migrated_tenants = set()


@contextmanager
def session_scope():
    """Provide one transactional scope around a series of operations."""
    tenant = _tenant_key()
    Session = _get_session(tenant)
    session = Session()
    try:
        if _tenancy_mode() != "single" and _is_postgres(_db_url()):
            _ensure_tenant_ready(tenant)

            from sqlalchemy import text

            session.execute(text(f"SET LOCAL search_path TO {tenant}"))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        Session.remove()


__all__ = ["reset_engine", "session_scope"]
