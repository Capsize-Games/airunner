import os
import re
from alembic.config import Config
from alembic import command
from pathlib import Path

from airunner.settings import AIRUNNER_DB_URL as DEFAULT_AIRUNNER_DB_URL


def _default_db_url() -> str:
    """Return the configured database URL with a fresh env lookup."""
    return os.environ.get("AIRUNNER_DATABASE_URL") or DEFAULT_AIRUNNER_DB_URL


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
        os.makedirs(db_dir, exist_ok=True)


def setup_database(db_url: str | None = None):
    target_db_url = db_url or _default_db_url()
    _ensure_sqlite_parent_dir(target_db_url)

    base = Path(os.path.dirname(os.path.realpath(__file__)))
    alembic_file = base / "alembic.ini"
    alembic_dir = base / "alembic"
    alembic_cfg = Config(alembic_file)
    alembic_cfg.set_main_option("script_location", str(alembic_dir))

    # Allow extensions to ship their own migrations.
    try:
        repo_root = base.parent.parent
        extensions_root = repo_root / "extensions"
        version_locations: list[str] = [str(alembic_dir / "versions")]
        if extensions_root.exists() and extensions_root.is_dir():
            for child in sorted(extensions_root.iterdir(), key=lambda p: p.name.lower()):
                versions_dir = child / "alembic" / "versions"
                if versions_dir.exists() and versions_dir.is_dir():
                    version_locations.append(str(versions_dir))
        alembic_cfg.set_main_option(
            "version_locations", os.pathsep.join(version_locations)
        )
    except Exception:
        pass

    # Alembic's Config wraps ConfigParser which treats '%' as interpolation.
    # SQLAlchemy URLs may contain percent-encoded sequences (e.g. %3D) when
    # we add Postgres connection options like search_path.
    safe_url = target_db_url.replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", safe_url)

    # Alembic's EnvironmentContext installs a proxy into modules that register
    # themselves via `EnvironmentContext.create_module_class_proxy()`.
    # Importing `alembic.context` up-front ensures it has registered before the
    # EnvironmentContext is entered, otherwise env.py may see an uninitialized
    # proxy (and `context.configure()` will fail).
    import alembic.context  # noqa: F401

    old_flag = os.environ.get("AIRUNNER_MIGRATION_RUNNING")
    os.environ["AIRUNNER_MIGRATION_RUNNING"] = "1"

    tenant_token = None
    if db_url:
        schema = _extract_search_path_schema(db_url)
        if schema:
            # session_manager derives schema as `<prefix><raw>`; if we're given a
            # full schema name, strip the prefix so session_scope stays in-sync.
            prefix = (os.environ.get("AIRUNNER_TENANT_SCHEMA_PREFIX") or "tenant_")
            raw_tenant = schema[len(prefix) :] if schema.startswith(prefix) else schema
            try:
                from airunner.components.data.tenant import set_tenant_key

                tenant_token = set_tenant_key(raw_tenant)
            except Exception:
                tenant_token = None

    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if tenant_token is not None:
            try:
                from airunner.components.data.tenant import reset_tenant_key

                reset_tenant_key(tenant_token)
            except Exception:
                pass

        if old_flag is None:
            os.environ.pop("AIRUNNER_MIGRATION_RUNNING", None)
        else:
            os.environ["AIRUNNER_MIGRATION_RUNNING"] = old_flag
