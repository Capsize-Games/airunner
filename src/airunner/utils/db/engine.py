from alembic import op
import sqlalchemy as sa


def get_connection():
    return op.get_bind()


def get_inspector():
    conn = get_connection()
    return sa.inspect(conn)
