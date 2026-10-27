"""Canonical database session management — PostgreSQL only.

Provides ``session_scope()`` and engine helpers used by the real
ORM layer (``RealBaseManager``).  The api layer uses these
directly; the bridge layer wraps calls through HTTP instead.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import pool
from sqlalchemy.orm import scoped_session, sessionmaker

from airunner_services.conf import settings as _settings
from airunner_services.database.db.engine import create_configured_engine

# Default database URL — resolved lazily through the settings module.
DEFAULT_AIRUNNER_DB_URL: str = ""


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def _db_url() -> str:
    """Return the active database URL from the settings module."""
    return _settings.DATABASE_URL


def _tenancy_mode() -> str:
    env_value = (os.environ.get("AIRUNNER_DB_TENANCY") or "").strip()
    if env_value:
        return env_value.lower()
    setting = str(getattr(_settings, "DB_TENANCY_MODE", "") or "").strip()
    return (setting or "single").lower()


def _is_postgres(url: str) -> bool:
    normalized = (url or "").lower()
    return normalized.startswith("postgresql") or normalized.startswith(
        "postgres"
    )


def _tenant_key() -> str:
    if _tenancy_mode() == "single":
        return "default"
    # Lazy import to avoid circular deps
    from airunner_services.data.tenant import (
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
_public_engine = None
_public_engine_url: str | None = None


def _ensure_tenant_ready(tenant: str) -> None:
    if _tenancy_mode() == "single":
        return
    if (os.environ.get("AIRUNNER_MIGRATION_RUNNING") or "").strip() == "1":
        return

    db_url = _db_url()
    if not _is_postgres(db_url) or tenant in _migrated_tenants:
        return

    from sqlalchemy import text
    from airunner_services.database.setup_database import (  # noqa: PLC0415
        setup_database,
    )

    base_engine = create_configured_engine(
        db_url,
        poolclass=pool.NullPool,
    )
    with base_engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {tenant}"))

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
        pool_size = int(os.environ.get("AIRUNNER_DB_POOL_SIZE", "20"))
        max_overflow = int(os.environ.get("AIRUNNER_DB_MAX_OVERFLOW", "40"))
        pool_timeout = int(os.environ.get("AIRUNNER_DB_POOL_TIMEOUT", "60"))
        pool_recycle = int(os.environ.get("AIRUNNER_DB_POOL_RECYCLE", "0"))

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

    global _public_engine, _public_engine_url
    if _public_engine is not None:
        try:
            _public_engine.dispose()
        except Exception:
            pass
    _public_engine = None
    _public_engine_url = None


def _get_public_engine():
    """Return a cached engine bound to the **public** schema.

    Built once per database URL and reused; creating a fresh engine (and
    therefore a fresh connection pool) on every ``public_session_scope``
    call leaks connections under load.
    """
    global _public_engine, _public_engine_url
    db_url = _db_url()
    if _public_engine is None or _public_engine_url != db_url:
        if _public_engine is not None:
            try:
                _public_engine.dispose()
            except Exception:
                pass
        _public_engine = create_configured_engine(
            db_url,
            pool_pre_ping=True,
        )
        _public_engine_url = db_url
    return _public_engine


@contextmanager
def session_scope():
    """Provide one transactional scope around a series of operations."""
    tenant = _tenant_key()
    Session = _get_session(tenant)
    session = Session()
    multitenant = _tenancy_mode() != "single" and _is_postgres(_db_url())
    listener = None
    try:
        if multitenant:
            _ensure_tenant_ready(tenant)

            from sqlalchemy import event, text

            # Re-apply the tenant search_path at the START of every transaction
            # in this session — not just once. `SET LOCAL` is transaction
            # scoped, so a single up-front SET is discarded by the first
            # commit(); any statement run afterwards (e.g. the post-commit
            # refresh() in base_manager.create()) would then hit the default
            # `public` schema and fail to find rows that live in the tenant
            # schema ("Could not refresh instance ...").
            def _apply_search_path(sess, transaction, connection):
                connection.exec_driver_sql(
                    f"SET LOCAL search_path TO {tenant}"
                )

            listener = _apply_search_path
            event.listen(session, "after_begin", listener)
            # Ensure the path is set for the first transaction too (after_begin
            # fires lazily on the first statement, which this triggers).
            session.execute(text(f"SET LOCAL search_path TO {tenant}"))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if listener is not None:
            from sqlalchemy import event

            event.remove(session, "after_begin", listener)
        Session.remove()


# ---------------------------------------------------------------------------
# Public schema session (for models outside tenant scope, e.g. Account)
# ---------------------------------------------------------------------------
@contextmanager
def public_session_scope():
    """Transactional scope for the **public** schema — bypasses tenants."""
    Session = scoped_session(sessionmaker(bind=_get_public_engine()))
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        Session.remove()


__all__ = [
    "reset_engine",
    "session_scope",
    "public_session_scope",
]
