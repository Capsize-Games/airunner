from alembic import op
import sqlalchemy as sa


def get_connection():
    return op.get_bind()

def is_sqlite() -> bool:
    return get_connection().dialect.name == 'sqlite'

def get_inspector():
    conn = get_connection()
    return sa.inspect(conn)