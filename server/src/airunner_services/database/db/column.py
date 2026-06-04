"""Column-level migration helpers owned by the service package."""

from __future__ import annotations

from typing import Any, Optional

from alembic import op
import sqlalchemy as sa

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.database.db.engine import get_inspector


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def get_columns(cls) -> list[str]:
    """Return current column names for one mapped table."""
    inspector = get_inspector()
    return [col["name"] for col in inspector.get_columns(cls.__tablename__)]


def column_exists(cls, column_name: str) -> bool:
    """Return whether one mapped column already exists in the database."""
    return column_name in get_columns(cls)


def add_column(cls, col: str) -> None:
    """Add one mapped column when it is not already present."""
    available_columns = cls.__table__.columns.keys()
    if not column_exists(cls, col) and col in available_columns:
        op.add_column(cls.__tablename__, getattr(cls, col))
        return
    logger.warning("Column '%s' already exists, skipping add.", col)


def add_columns(cls, cols: list[str]) -> None:
    """Add several mapped columns when missing."""
    for col in cols:
        add_column(cls, col)


def _foreign_keys_for_column(cls, col: str) -> list[dict[str, Any]]:
    """Return foreign keys that constrain one mapped column."""
    inspector = get_inspector()
    foreign_keys = inspector.get_foreign_keys(cls.__tablename__)
    return [
        fk for fk in foreign_keys if col in fk.get("constrained_columns", [])
    ]


def _drop_named_foreign_keys(batch_op, cls, col: str) -> None:
    """Drop named foreign keys before removing one column."""
    for foreign_key in _foreign_keys_for_column(cls, col):
        name = foreign_key.get("name")
        if name:
            batch_op.drop_constraint(name, type_="foreignkey")
            continue
        logger.warning(
            "Skipping unnamed foreign key constraint on column '%s' "
            "(cannot drop by name)",
            col,
        )


def drop_column(cls, col: str) -> None:
    """Drop one mapped column when it exists."""
    if not column_exists(cls, col):
        logger.warning("Column '%s' does not exist, skipping drop.", col)
        return

    with op.batch_alter_table(cls.__tablename__, recreate="auto") as batch_op:
        _drop_named_foreign_keys(batch_op, cls, col)
        batch_op.drop_column(col)


def drop_columns(cls, cols: list[str]) -> None:
    """Drop several mapped columns when they exist."""
    for col in cols:
        drop_column(cls, col)


def alter_column(
    cls,
    col_a: sa.Column,
    col_b: sa.Column,
) -> None:
    """Alter one mapped column type when it actually changed."""
    if getattr(cls, col_a.name).type == col_b.type:
        logger.warning(
            "Column '%s' already has the same type as '%s', "
            "skipping modify.",
            col_a,
            col_b,
        )
        return

    with op.batch_alter_table(cls.__tablename__, recreate="auto") as batch_op:
        batch_op.alter_column(
            col_a.name,
            existing_type=getattr(cls, col_a.name).type,
            type_=col_b.type,
            nullable=col_b.nullable,
        )


def add_column_with_fk(
    cls,
    column_name: str,
    column_type: sa.Column,
    fk_table: str,
    fk_column: str,
    fk_name: str,
) -> None:
    """Add one column and attach one foreign-key constraint."""
    if column_exists(cls, column_name):
        return
    with op.batch_alter_table(cls.__tablename__, recreate="always") as batch_op:
        batch_op.add_column(sa.Column(column_name, column_type))
        batch_op.create_foreign_key(
            fk_name,
            fk_table,
            [column_name],
            [fk_column],
        )


def drop_column_with_fk(cls, column_name: str, fk_name: str) -> None:
    """Drop one foreign-key column and its named constraint."""
    if not column_exists(cls, column_name):
        logger.warning(
            "Column '%s' does not exist, skipping drop.",
            column_name,
        )
        return

    fk_exists = any(
        fk.get("name") == fk_name
        for fk in _foreign_keys_for_column(cls, column_name)
    )
    with op.batch_alter_table(cls.__tablename__, recreate="auto") as batch_op:
        if fk_exists:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        batch_op.drop_column(column_name)


def safe_alter_column(
    cls,
    column_name: str,
    new_type: Optional[sa.types.TypeEngine] = None,
    existing_type: Optional[sa.types.TypeEngine] = None,
    nullable: bool = False,
    existing_server_default: Optional[Any] = None,
) -> None:
    """Alter one column with best-effort guards for live schemas."""
    if not column_exists(cls, column_name):
        logger.warning(
            "Column '%s' does not exist, skipping alter.",
            column_name,
        )
        return

    options: dict[str, Any] = {"nullable": nullable}
    if existing_type is not None:
        options["existing_type"] = existing_type
    if new_type is not None:
        options["type_"] = new_type
    if existing_server_default is not None:
        options["server_default"] = existing_server_default

    try:
        with op.batch_alter_table(cls.__tablename__, recreate="auto") as batch_op:
            batch_op.alter_column(column_name, **options)
    except sa.exc.OperationalError as exc:
        logger.error("Error altering column '%s': %s", column_name, exc)


def safe_alter_columns(cls, columns: list[sa.Column]) -> None:
    """Alter several mapped columns with safe guards."""
    for column in columns:
        safe_alter_column(
            cls,
            column.name,
            column.type,
            column.type,
            column.nullable,
        )


def set_default_and_create_fk(
    table_name,
    column_name,
    ref_table_name,
    ref_column_name,
    default_value,
) -> None:
    """Backfill one FK column with a default before tightening schema."""
    op.execute(
        f"""
        UPDATE {table_name}
        SET {column_name} = {default_value}
        WHERE {column_name} IS NULL
        OR {column_name} NOT IN (
            SELECT {ref_column_name} FROM {ref_table_name}
        )
        """
    )
    safe_alter_column(
        table_name,
        column_name,
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text(str(default_value)),
    )


def set_default(cls, column_name: str, default_value: Any) -> None:
    """Apply one server default to one mapped column."""
    safe_alter_column(
        cls,
        column_name,
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text(str(default_value)),
    )


def _dialect_name() -> str:
    """Return the active Alembic dialect name."""
    return getattr(getattr(op.get_bind(), "dialect", None), "name", "")


def create_unique_constraint(
    cls,
    columns: list[str],
    constraint_name: str,
) -> None:
    """Create one unique constraint on one mapped table."""
    table_name = cls.__tablename__
    try:
        if _dialect_name() == "sqlite":
            with op.batch_alter_table(table_name, recreate="always") as batch_op:
                batch_op.create_unique_constraint(constraint_name, columns)
        else:
            op.create_unique_constraint(constraint_name, table_name, columns)
        logger.info(
            "Unique constraint '%s' created on table '%s' for columns %s.",
            constraint_name,
            table_name,
            columns,
        )
    except sa.exc.OperationalError as exc:
        logger.error(
            "Error creating unique constraint '%s' on table '%s': %s",
            constraint_name,
            table_name,
            exc,
        )
    except NotImplementedError as exc:
        logger.error("SQLite limitation: %s", exc)


def drop_constraint(
    cls,
    constraint_name: str,
    constraint_type: str = "unique",
) -> None:
    """Drop one named constraint from one mapped table."""
    table_name = cls.__tablename__
    try:
        if _dialect_name() == "sqlite":
            with op.batch_alter_table(table_name, recreate="always") as batch_op:
                batch_op.drop_constraint(
                    constraint_name,
                    type_=constraint_type,
                )
        else:
            op.drop_constraint(
                constraint_name,
                table_name,
                type_=constraint_type,
            )
        logger.info(
            "Constraint '%s' of type '%s' dropped from table '%s'.",
            constraint_name,
            constraint_type,
            table_name,
        )
    except sa.exc.OperationalError as exc:
        logger.error(
            "Error dropping constraint '%s' from table '%s': %s",
            constraint_name,
            table_name,
            exc,
        )
    except NotImplementedError as exc:
        logger.error("SQLite limitation: %s", exc)


__all__ = [
    "add_column",
    "add_column_with_fk",
    "add_columns",
    "alter_column",
    "column_exists",
    "create_unique_constraint",
    "drop_column",
    "drop_column_with_fk",
    "drop_columns",
    "drop_constraint",
    "get_columns",
    "safe_alter_column",
    "safe_alter_columns",
    "set_default",
    "set_default_and_create_fk",
]
