from alembic import op
import sqlalchemy as sa
from typing import List
from airunner.utils.db.engine import get_inspector
from airunner.utils.db.engine import is_sqlite


def get_columns(cls) -> List[str]:
    inspector = get_inspector()
    columns = [col['name'] for col in inspector.get_columns(cls.__tablename__)]
    return columns
    

def column_exists(cls, column_name):
    return column_name in get_columns(cls)

def add_column(cls, col):
    available_columns = cls.__table__.columns.keys()
    if not column_exists(cls, col) and col in available_columns:
        op.add_column(cls.__tablename__, getattr(cls, col))
    else:
        print(f"Column '{col}' already exists, skipping add.")


def add_columns(cls, cols):
    for col in cols:
        add_column(cls, col)


def drop_column(cls, col):
    if column_exists(cls, col):
        inspector = get_inspector()
        foreign_keys = inspector.get_foreign_keys(cls.__tablename__)

        if is_sqlite():
            with op.batch_alter_table(cls.__tablename__) as batch_op:
                for fk in foreign_keys:
                    if col in fk['constrained_columns']:
                        batch_op.drop_constraint(fk['name'], type_='foreignkey')
                batch_op.drop_column(col)
        else:
            for fk in foreign_keys:
                if col in fk['constrained_columns']:
                    op.drop_constraint(fk['name'], cls.__tablename__, type_='foreignkey')
            op.drop_column(cls.__tablename__, col)
    else:
        print(f"Column '{col}' does not exist, skipping drop.")


def drop_columns(cls, cols):
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

    if is_sqlite():
        with op.batch_alter_table(cls.__tablename__) as batch_op:
            batch_op.alter_column(
                col_a.name,
                existing_type=getattr(cls, col_a.name).type,
                type_=col_b.type,
                nullable=col_b.nullable
            )
    else:
        op.alter_column(
            cls.__tablename__, 
            col_a.name,
            existing_type=getattr(cls, col_a.name).type,
            type_=col_b.type,
            nullable=col_b.nullable
        )