from typing import Optional
from alembic import op
import sqlalchemy as sa


def get_tables():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return inspector.get_table_names()


def table_exists(table_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def add_table(cls):
    if not table_exists(cls.__tablename__):
        columns = [column.copy() for column in cls.__table__.columns]
        op.create_table(cls.__tablename__, *columns, *getattr(cls, '__table_args__', ()))
    else:
        print(f"Table '{cls.__tablename__}' already exists, skipping add.")
    return


def add_tables(classes):
    for cls in classes:
        create_table_with_defaults(cls)
    return


def drop_table(cls: Optional[object] = None, table_name: Optional[str] = None):
    if cls is not None:
        table_name = cls.__tablename__
    if table_exists(table_name):
        op.drop_table(table_name)
    else:
        print(f"Table '{table_name}' does not exist, skipping drop.")
    return


def drop_tables(classes):
    for cls in classes:
        drop_table(cls)
    return


def create_table_with_defaults(model):
    if not table_exists(model.__tablename__):
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
                *getattr(model, '__table_args__', ())
            )
            set_default_values(model)
        except Exception as e:
            print(f"Failed to create table {model.__tablename__}: {str(e)}")
    else:
        print(f"{model.__tablename__} already exists, skipping")


def set_default_values(model):
    default_values = {}
    for column in model.__table__.columns:
        if column.default is not None:
            default_values[column.name] = column.default.arg
    op.bulk_insert(
        model.__table__,
        [default_values]
    )
