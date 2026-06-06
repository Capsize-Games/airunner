"""Table-level migration helpers owned by the service package."""

from __future__ import annotations

from typing import Optional

from alembic import op
import sqlalchemy as sa

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _inspector():
    """Return one SQLAlchemy inspector for the active Alembic bind."""
    return sa.inspect(op.get_bind())


def get_tables() -> list[str]:
    """Return table names visible to the active Alembic bind."""
    return _inspector().get_table_names()


def table_exists(table_name: str) -> bool:
    """Return whether one table already exists."""
    return table_name in get_tables()


def add_table(cls) -> None:
    """Create one mapped table when it is missing."""
    if table_exists(cls.__tablename__):
        logger.warning(
            "Table '%s' already exists, skipping add.",
            cls.__tablename__,
        )
        return
    columns = [column.copy() for column in cls.__table__.columns]
    op.create_table(
        cls.__tablename__,
        *columns,
        *getattr(cls, "__table_args__", ()),
    )


def add_tables(classes) -> None:
    """Create several mapped tables and seed their defaults."""
    for cls in classes:
        create_table_with_defaults(cls)


def drop_table(
    cls: Optional[object] = None,
    table_name: Optional[str] = None,
) -> None:
    """Drop one table by mapped class or explicit name."""
    if cls is not None:
        table_name = cls.__tablename__
    if table_name and table_exists(table_name):
        op.drop_table(table_name)
        return
    logger.warning("Table '%s' does not exist, skipping drop.", table_name)


def drop_tables(classes) -> None:
    """Drop several mapped tables."""
    for cls in classes:
        drop_table(cls)


def create_table_with_defaults(model) -> None:
    """Create one mapped table and insert one row of default values."""
    if table_exists(model.__tablename__):
        logger.warning("%s already exists, skipping", model.__tablename__)
        return
    try:
        columns = []
        for column in model.__table__.columns:
            column_copy = column.copy()
            if column.default is not None:
                column_copy.server_default = column.default
            columns.append(column_copy)
        op.create_table(
            model.__tablename__,
            *columns,
            *getattr(model, "__table_args__", ()),
        )
        set_default_values(model)
    except Exception as exc:
        logger.error(
            "Failed to create table %s: %s",
            model.__tablename__,
            exc,
        )


def set_default_values(model) -> None:
    """Insert one row containing mapped Python default values."""
    default_values = {}
    for column in model.__table__.columns:
        if column.default is not None:
            default_values[column.name] = column.default.arg
    op.bulk_insert(model.__table__, [default_values])


__all__ = [
    "add_table",
    "add_tables",
    "create_table_with_defaults",
    "drop_table",
    "drop_tables",
    "get_tables",
    "set_default_values",
    "table_exists",
]
