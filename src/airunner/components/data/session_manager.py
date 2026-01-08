import os

from contextlib import contextmanager
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import pool

from airunner.settings import AIRUNNER_DB_URL


def _tenancy_mode() -> str:
    return (os.environ.get("AIRUNNER_DB_TENANCY", "single") or "single").strip().lower()


def _is_postgres(url: str) -> bool:
    u = (url or "").lower()
    return u.startswith("postgresql") or u.startswith("postgres")


def _tenant_key() -> str:
    if _tenancy_mode() == "single":
        return "default"

    from airunner.components.data.tenant import get_tenant_key, tenant_schema_for_key

    raw = get_tenant_key()
    # Default tenant when no header is provided.
    return tenant_schema_for_key(raw)


def _tenant_db_url(base_url: str, tenant_schema: str) -> str:
    """Build a per-tenant DB URL.

    For Postgres, we use search_path via `options=-csearch_path=<schema>`.
    """
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
    # IMPORTANT: `str(URL)` masks the password as '***'. We need the real
    # password here because Alembic creates a new Engine from this URL.
    return new_url.render_as_string(hide_password=False)


# Lazy-initialized globals
_engines: dict[str, object] = {}
_sessions: dict[str, scoped_session] = {}
_migrated_tenants: set[str] = set()


def _ensure_tenant_ready(tenant: str) -> None:
    # Only required for Postgres schema tenancy.
    if _tenancy_mode() == "single":
        return

    # Avoid recursive migrations (some Alembic revisions call ORM helpers which
    # use session_scope()). When we're already running migrations, the schema is
    # being brought up-to-date by the outer Alembic run.
    if (os.environ.get("AIRUNNER_MIGRATION_RUNNING") or "").strip() == "1":
        return

    if not _is_postgres(AIRUNNER_DB_URL):
        return

    if tenant in _migrated_tenants:
        return

    # Best-effort initialize tenant schema and run migrations.
    #
    # Important: do not use a pooled Engine here.
    # Creating a new pooled engine per tenant can easily exhaust Postgres
    # connections (each Engine creates its own pool). NullPool ensures we open
    # only what we need for this one-off DDL/migration.
    from sqlalchemy import text
    from airunner.setup_database import setup_database

    # Create schema in the base DB (public search_path).
    base_engine = create_engine(AIRUNNER_DB_URL, poolclass=pool.NullPool)
    with base_engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {tenant}"))

    tenant_url = _tenant_db_url(AIRUNNER_DB_URL, tenant)
    setup_database(db_url=tenant_url)
    _migrated_tenants.add(tenant)


def _get_engine(tenant: str):
    """Get or create the SQLAlchemy engine.

    Lazy initialization ensures the engine uses the correct database URL
    from environment variables, even if they are set after module import.
    This is critical for testing where AIRUNNER_DATABASE_URL is set by
    pytest fixtures.
    """
    # Under Postgres schema tenancy, do NOT create an Engine per tenant.
    # That would create an unbounded number of connection pools.
    # Instead, use a single shared engine and set search_path per session.
    engine_key = tenant
    if _tenancy_mode() != "single" and _is_postgres(AIRUNNER_DB_URL):
        engine_key = "__shared__"

    if engine_key not in _engines:
        # AI Runner is frequently used under streaming workloads. The default
        # SQLAlchemy QueuePool settings (pool_size=5, max_overflow=10,
        # pool_timeout=30) are too small for a multi-request dev stack and can
        # lead to timeouts when chat history/checkpoints are being persisted.
        #
        # Allow tuning via env vars while keeping safe defaults.
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

        _engines[engine_key] = create_engine(AIRUNNER_DB_URL, **engine_kwargs)

    return _engines[engine_key]


def _get_session(tenant: str):
    """Get or create the scoped session factory."""
    if tenant not in _sessions:
        _sessions[tenant] = scoped_session(sessionmaker(bind=_get_engine(tenant)))
    return _sessions[tenant]


def reset_engine():
    """Reset the engine and session.

    Forces recreation of database connections. Useful for tests that change
    the database URL via environment variables.
    """
    global _engines, _sessions, _migrated_tenants
    for s in list(_sessions.values()):
        try:
            s.remove()
        except Exception:
            pass
    _sessions = {}

    for e in list(_engines.values()):
        try:
            e.dispose()
        except Exception:
            pass
    _engines = {}
    _migrated_tenants = set()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    tenant = _tenant_key()
    Session = _get_session(tenant)
    session = Session()
    try:
        if _tenancy_mode() != "single" and _is_postgres(AIRUNNER_DB_URL):
            # Ensure schema + migrations exist, then scope this transaction to
            # the tenant schema.
            _ensure_tenant_ready(tenant)
            from sqlalchemy import text

            session.execute(text(f"SET LOCAL search_path TO {tenant}"))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
