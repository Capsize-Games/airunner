from alembic import op
import sqlalchemy as sa
from sqlalchemy import create_engine, event


SQLITE_BUSY_TIMEOUT_MS = 5000


def _is_sqlite_url(db_url: object) -> bool:
    """Return True when the target engine uses SQLite."""
    return str(db_url).lower().startswith("sqlite")


def _configure_sqlite_connection(
    dbapi_connection,
    _connection_record,
) -> None:
    """Apply per-connection SQLite pragmas for concurrent local access."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()


def create_configured_engine(db_url: object, **kwargs):
    """Create one SQLAlchemy engine with AIRunner defaults applied."""
    engine = create_engine(db_url, **kwargs)
    if _is_sqlite_url(db_url):
        event.listen(engine, "connect", _configure_sqlite_connection)
    return engine


def get_connection():
    return op.get_bind()


def get_inspector():
    conn = get_connection()
    return sa.inspect(conn)
