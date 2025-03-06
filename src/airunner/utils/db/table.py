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
        op.create_table(cls.__tablename__, *cls.__table_args__)
    else:
        print(f"Table '{cls.__tablename__}' already exists, skipping add.")
    return

def add_tables(classes):
    for cls in classes:
        add_table(cls)
    return

def drop_table(cls):
    if table_exists(cls.__tablename__):
        op.drop_table(cls.__tablename__)
    else:
        print(f"Table '{cls.__tablename__}' does not exist, skipping drop.")
    return

def create_table(cls):
    if not table_exists(cls.__tablename__):
        op.create_table(cls.__tablename__, *cls.__table_args__)
    else:
        print(f"Table '{cls.__tablename__}' already exists, skipping create.")
    return

def create_table_with_defaults(model):
    if not table_exists(model.__tablename__):
        try:
            op.create_table(
                model.__tablename__,
                *model.__table__.columns
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