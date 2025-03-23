from typing import Optional, Any
from alembic import op
import sqlalchemy as sa
from typing import List
from airunner.utils.db.engine import get_inspector


def get_columns(cls) -> List[str]:
    inspector = get_inspector()
    columns = [col['name'] for col in inspector.get_columns(cls.__tablename__)]
    return columns
    

def column_exists(cls, column_name: str) -> bool:
    return column_name in get_columns(cls)


def add_column(cls, col: str):
    available_columns = cls.__table__.columns.keys()
    if not column_exists(cls, col) and col in available_columns:
        op.add_column(cls.__tablename__, getattr(cls, col))
    else:
        print(f"Column '{col}' already exists, skipping add.")


def add_columns(cls, cols: List[str]):
    for col in cols:
        add_column(cls, col)


def drop_column(cls, col: str):
    if column_exists(cls, col):
        inspector = get_inspector()
        foreign_keys = inspector.get_foreign_keys(cls.__tablename__)

        with op.batch_alter_table(cls.__tablename__, recreate='auto') as batch_op:
            for fk in foreign_keys:
                if col in fk['constrained_columns']:
                    batch_op.drop_constraint(fk['name'], type_='foreignkey')
            batch_op.drop_column(col)
    else:
        print(f"Column '{col}' does not exist, skipping drop.")


def drop_columns(cls, cols: List[str]):
    for col in cols:
        drop_column(cls, col)


def alter_column(
    cls, 
    col_a: sa.Column, 
    col_b: sa.Column, 
):
    # check if column already equals new column
    if getattr(cls, col_a.name).type == col_b.type:
        print(f"Column '{col_a}' already has the same type as '{col_b}', skipping modify.")
        return

    with op.batch_alter_table(cls.__tablename__, recreate='auto') as batch_op:
        batch_op.alter_column(
            col_a.name,
            existing_type=getattr(cls, col_a.name).type,
            type_=col_b.type,
            nullable=col_b.nullable
        )


def add_column_with_fk(
    cls,
    column_name: str, 
    column_type: sa.Column, 
    fk_table: str, 
    fk_column: str, 
    fk_name: str
) -> None:
    """
    Adds a column with a foreign key constraint to a table.

    :param cls: SQLAlchemy model class.
    :param column_name: Name of the new column.
    :param column_type: SQLAlchemy column type for the new column.
    :param fk_table: Name of the foreign key table.
    :param fk_column: Name of the foreign key column.
    :param fk_name: Name of the foreign key constraint.
    """
    if not column_exists(cls, column_name):
        with op.batch_alter_table(cls.__tablename__, recreate='always') as batch_op:
            batch_op.add_column(sa.Column(column_name, column_type))
            batch_op.create_foreign_key(fk_name, fk_table, [column_name], [fk_column])


def drop_column_with_fk(
    cls,
    column_name: str,
    fk_name: str
) -> None:
    """
    Drops a column with a foreign key constraint from a table.

    :param cls: SQLAlchemy model class.
    :param column_name: Name of the column to drop.
    :param fk_name: Name of the foreign key constraint.
    """
    if column_exists(cls, column_name):
        inspector = get_inspector()
        foreign_keys = inspector.get_foreign_keys(cls.__tablename__)
        fk_exists = any(fk['name'] == fk_name for fk in foreign_keys)

        with op.batch_alter_table(cls.__tablename__, recreate='auto') as batch_op:
            if fk_exists:
                batch_op.drop_constraint(fk_name, type_='foreignkey')
            batch_op.drop_column(column_name)
    else:
        print(f"Column '{column_name}' does not exist, skipping drop.")


def safe_alter_column(
    cls, 
    column_name: str, 
    new_type: Optional[sa.types.TypeEngine] = None, 
    existing_type: Optional[sa.types.TypeEngine] = None, 
    nullable: bool = False,
    existing_server_default: Optional[Any] = None
):
    if not column_exists(cls, column_name):
        print(f"Column '{column_name}' does not exist, skipping alter.")
        return

    options = dict(
        nullable=nullable,
    )

    if existing_type:
        options['existing_type'] = existing_type

    if new_type:
        options['type_'] = new_type

    if existing_server_default is not None:
        options['server_default'] = existing_server_default

    try:
        with op.batch_alter_table(
            cls.__tablename__, 
            recreate='auto'
        ) as batch_op:
            batch_op.alter_column(
                column_name,
                **options
            )
    except sa.exc.OperationalError as e:
        print(f"Error altering column '{column_name}'", e)


def safe_alter_columns(cls, columns: List[sa.Column]):
    for column in columns:
        safe_alter_column(
            cls, 
            column.name, 
            column.type, 
            column.type, 
            column.nullable
        )


def set_default_and_create_fk(
    table_name, 
    column_name, 
    ref_table_name, 
    ref_column_name, 
    default_value
):
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
        existing_server_default=sa.text(str(default_value))
    )

def set_default(
    cls,
    column_name: str,
    default_value: Any
) -> None:
    """
    Sets a default value for a column in a table.
    """
    safe_alter_column(
        cls,
        column_name,
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text(str(default_value))
    )


def create_unique_constraint(
    cls, 
    columns: List[str], 
    constraint_name: str
) -> None:
    """
    Creates a unique constraint on the specified columns of a table.

    :param cls: SQLAlchemy model class.
    :param constraint_name: Name of the unique constraint.
    :param columns: List of column names to include in the unique constraint.
    """
    table_name = cls.__tablename__
    try:
        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            batch_op.create_unique_constraint(constraint_name, columns)
        print(
            f"Unique constraint '{constraint_name}' "
            f"created on table '{table_name}' for columns {columns}."
        )
    except sa.exc.OperationalError as e:
        print(f"Error creating unique constraint '{constraint_name}' on table '{table_name}':", e)
    except NotImplementedError as e:
        print(f"SQLite limitation: {e}")


def drop_constraint(
    cls, 
    constraint_name: str, 
    constraint_type: str = "unique"
) -> None:
    """
    Drops a constraint from the specified table.

    :param cls: SQLAlchemy model class.
    :param constraint_name: Name of the constraint to drop.
    :param constraint_type: Type of the constraint (e.g., 'unique', 'foreignkey', etc.).
    """
    table_name = cls.__tablename__
    try:
        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            batch_op.drop_constraint(constraint_name, type_=constraint_type)
        print(f"Constraint '{constraint_name}' of type '{constraint_type}' dropped from table '{table_name}'.")
    except sa.exc.OperationalError as e:
        print(f"Error dropping constraint '{constraint_name}' from table '{table_name}':", e)
    except NotImplementedError as e:
        print(f"SQLite limitation: {e}")
