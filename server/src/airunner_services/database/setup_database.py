import json
import os
import re
import threading
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pathlib import Path
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from airunner_services.conf import settings as _settings
from airunner_services.database.db.engine import create_configured_engine

AIRUNNER_BASE_PATH = _settings.AIRUNNER_BASE_PATH
DEFAULT_AIRUNNER_DB_URL = _settings.AIRUNNER_DB_URL

_SETUP_LOCK = threading.Lock()
_COMPLETED_SETUP_URLS: set[str] = set()


def _ensure_private_directory(path: str | Path) -> None:
    """Create one directory with best-effort user-only permissions."""
    os.makedirs(path, exist_ok=True, mode=0o700)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _default_db_url() -> str:
    """Return the configured database URL from settings."""
    return _settings.DATABASE_URL


def _extract_search_path_schema(db_url: str) -> str | None:
    try:
        from sqlalchemy.engine import make_url

        url = make_url(db_url)
        options = (dict(url.query or {}).get("options") or "").strip()
        if not options:
            return None
        match = re.search(r"(?:^|\s)-csearch_path=([^\s]+)", options)
        if not match:
            return None
        return match.group(1)
    except Exception:
        return None


def _ensure_sqlite_parent_dir(db_url: str) -> None:
    if not db_url.startswith("sqlite:///"):
        return

    db_path = db_url.replace("sqlite:///", "", 1)
    db_dir = os.path.dirname(db_path)
    if db_dir:
        _ensure_private_directory(db_dir)


def _use_setup_cache() -> bool:
    """Return whether repeated setup calls should be skipped."""
    return os.environ.get("AIRUNNER_DISABLE_DB_SETUP_CACHE", "0") != "1"


def _version_locations(base: Path, alembic_dir: Path) -> list[Path]:
    """Return the migration version directories for core."""
    return [alembic_dir / "versions"]


def _migration_heads_cache_path() -> Path:
    """Return the on-disk cache path for discovered migration heads."""
    cache_dir = Path(AIRUNNER_BASE_PATH) / "data"
    _ensure_private_directory(cache_dir)
    return cache_dir / "migration_heads.json"


def _migration_signature(
    version_locations: list[Path],
    base: Path,
) -> str:
    """Return a stable signature for all migration files on disk."""
    parts: list[str] = []
    for version_dir in version_locations:
        if not version_dir.exists():
            continue
        for migration_file in sorted(version_dir.glob("*.py")):
            stat = migration_file.stat()
            relative_path = migration_file.relative_to(base)
            parts.append(f"{relative_path}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def _read_cached_migration_heads(signature: str) -> tuple[str, ...]:
    """Return cached heads when the migration signature is unchanged."""
    cache_path = _migration_heads_cache_path()
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return ()

    if payload.get("signature") != signature:
        return ()
    heads = payload.get("heads") or []
    return tuple(sorted(str(head) for head in heads))


def _write_cached_migration_heads(
    signature: str,
    heads: tuple[str, ...],
) -> None:
    """Persist the discovered heads for the current migration signature."""
    cache_path = _migration_heads_cache_path()
    payload = {
        "signature": signature,
        "heads": list(heads),
    }
    cache_path.write_text(json.dumps(payload), encoding="utf-8")


def _expected_migration_heads(alembic_cfg: Config) -> tuple[str, ...]:
    """Return the sorted Alembic heads for the configured scripts."""
    script_dir = ScriptDirectory.from_config(alembic_cfg)
    return tuple(sorted(script_dir.get_heads()))


def _cached_expected_migration_heads(
    alembic_cfg: Config,
    version_locations: list[Path],
    base: Path,
) -> tuple[str, ...]:
    """Return expected heads, using a persistent cache when possible."""
    signature = _migration_signature(version_locations, base)
    cached_heads = _read_cached_migration_heads(signature)
    if cached_heads:
        return cached_heads

    expected_heads = _expected_migration_heads(alembic_cfg)
    if expected_heads:
        _write_cached_migration_heads(signature, expected_heads)
    return expected_heads


def _current_database_heads(target_db_url: str) -> tuple[str, ...]:
    """Return the sorted migration heads currently recorded in the DB."""
    engine = create_configured_engine(target_db_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return tuple(sorted(context.get_current_heads()))
    finally:
        engine.dispose()


def _database_is_at_head(
    alembic_cfg: Config,
    target_db_url: str,
    version_locations: list[Path],
    base: Path,
) -> bool:
    """Return whether the database already matches the latest heads."""
    try:
        expected_heads = _cached_expected_migration_heads(
            alembic_cfg,
            version_locations,
            base,
        )
        if not expected_heads:
            return False
        current_heads = _current_database_heads(target_db_url)
        return current_heads == expected_heads
    except Exception:
        return False


def _core_startup_models() -> tuple[type[object], ...]:
    """Return singleton models required for safe GUI startup."""
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )
    from airunner_services.database.models.path_settings import PathSettings

    return (PathSettings, ApplicationSettings)


def _ensure_startup_rows(engine) -> None:
    """Create default singleton rows required during startup."""
    Session = sessionmaker(bind=engine)
    with Session() as session:
        created = False
        for model in _core_startup_models():
            if session.query(model).first() is None:
                session.add(model())
                created = True
        if created:
            session.commit()


def _extension_model_classes() -> list:
    """Return extension models that should be created in the target schema.

    Models with ``__public_schema__ = True`` are excluded here; they
    are handled separately in the public schema setup.
    """
    from airunner_services.extensions.loader import (  # noqa: PLC0415
        get_extension_models,
    )

    return [
        m
        for m in get_extension_models()
        if not getattr(m, "__public_schema__", False)
    ]


def _extension_public_model_classes() -> list:
    """Return extension models that belong in the **public** schema."""
    from airunner_services.extensions.loader import (  # noqa: PLC0415
        get_extension_models,
    )

    return [
        m
        for m in get_extension_models()
        if getattr(m, "__public_schema__", False)
    ]


def _repair_application_schema(target_db_url: str) -> None:
    """Ensure core application tables exist even on pristine databases."""
    import airunner_services.database.models as model_module
    from airunner_services.database.base import Base

    # Collect all model classes exported from the models package.
    _model_classes = [
        getattr(model_module, name)
        for name in model_module.__all__
        if hasattr(getattr(model_module, name), "__tablename__")
    ]
    # Append extension models (non-public-schema).
    _model_classes.extend(_extension_model_classes())

    engine = create_configured_engine(target_db_url)
    try:
        existing_tables = set(inspect(engine).get_table_names())
        missing_tables = [
            model.__table__
            for model in _model_classes
            if model.__tablename__ not in existing_tables
        ]
        if missing_tables:
            Base.metadata.create_all(
                bind=engine,
                tables=missing_tables,
                checkfirst=True,
            )
        _ensure_startup_rows(engine)
    finally:
        engine.dispose()


def _append_extension_migration_paths(version_locations: list[Path]) -> None:
    """Append extension Alembic version directories to the locations list."""
    from airunner_services.extensions.loader import (  # noqa: PLC0415
        get_extension_migration_paths,
    )

    for ext_path in get_extension_migration_paths():
        versions_dir = ext_path / "versions"
        if versions_dir.is_dir():
            version_locations.append(ext_path)


def _setup_public_schema_tables(target_db_url: str) -> None:
    """Create extension tables that belong to the **public** schema.

    Only relevant for PostgreSQL multi-tenant mode.  In single-tenant
    mode the public schema tables are created alongside tenant tables
    via _repair_application_schema.
    """
    import sqlalchemy as sa  # noqa: PLC0415
    from airunner_services.database.base import Base  # noqa: PLC0415

    models = _extension_public_model_classes()
    if not models:
        return

    engine = create_configured_engine(target_db_url)
    try:
        existing = set(sa.inspect(engine).get_table_names())
        missing = [
            m.__table__ for m in models if m.__tablename__ not in existing
        ]
        if missing:
            Base.metadata.create_all(
                bind=engine,
                tables=missing,
                checkfirst=True,
            )
    finally:
        engine.dispose()


def setup_database(db_url: str | None = None):
    target_db_url = db_url or _default_db_url()
    _ensure_sqlite_parent_dir(target_db_url)

    if _use_setup_cache() and target_db_url in _COMPLETED_SETUP_URLS:
        return

    base = Path(os.path.dirname(os.path.realpath(__file__)))
    alembic_file = base / "alembic.ini"
    alembic_dir = base / "alembic"
    with _SETUP_LOCK:
        if _use_setup_cache() and target_db_url in _COMPLETED_SETUP_URLS:
            return

        alembic_cfg = Config(alembic_file)
        alembic_cfg.set_main_option("script_location", str(alembic_dir))
        version_locations = _version_locations(base, alembic_dir)

        # Append extension migration directories so Alembic discovers
        # their version files.
        _append_extension_migration_paths(version_locations)

        # Allow extensions to ship their own migrations.
        try:
            alembic_cfg.set_main_option(
                "version_locations",
                os.pathsep.join(str(path) for path in version_locations),
            )
        except Exception:
            pass

        # Alembic's Config wraps ConfigParser which treats '%' as interpolation.
        # SQLAlchemy URLs may contain percent-encoded sequences (e.g. %3D) when
        # we add Postgres connection options like search_path.
        safe_url = target_db_url.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", safe_url)

        if _database_is_at_head(
            alembic_cfg,
            target_db_url,
            version_locations,
            base,
        ):
            _repair_application_schema(target_db_url)
            if _use_setup_cache():
                _COMPLETED_SETUP_URLS.add(target_db_url)
            return

        # Alembic's EnvironmentContext installs a proxy into modules that
        # register themselves via create_module_class_proxy(). Importing
        # alembic.context up-front ensures it has registered before env.py runs.
        import alembic.context  # noqa: F401

        old_flag = os.environ.get("AIRUNNER_MIGRATION_RUNNING")
        os.environ["AIRUNNER_MIGRATION_RUNNING"] = "1"

        tenant_token = None
        if db_url:
            schema = _extract_search_path_schema(db_url)
            if schema:
                prefix = (
                    os.environ.get("AIRUNNER_TENANT_SCHEMA_PREFIX")
                    or "tenant_"
                )
                raw_tenant = (
                    schema[len(prefix) :]
                    if schema.startswith(prefix)
                    else schema
                )
                try:
                    from airunner_services.data.tenant import set_tenant_key

                    tenant_token = set_tenant_key(raw_tenant)
                except Exception:
                    tenant_token = None

        try:
            command.upgrade(alembic_cfg, "heads")
        finally:
            if tenant_token is not None:
                try:
                    from airunner_services.data.tenant import reset_tenant_key

                    reset_tenant_key(tenant_token)
                except Exception:
                    pass

            if old_flag is None:
                os.environ.pop("AIRUNNER_MIGRATION_RUNNING", None)
            else:
                os.environ["AIRUNNER_MIGRATION_RUNNING"] = old_flag

        _repair_application_schema(target_db_url)
        _setup_public_schema_tables(target_db_url)

        if _use_setup_cache():
            _COMPLETED_SETUP_URLS.add(target_db_url)
