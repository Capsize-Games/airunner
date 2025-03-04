from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '75020956e3e2'
down_revision: Union[str, None] = '26a0d29a3af3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def convert_image_to_binary(image_path):
    with open(image_path, 'rb') as file:
        binary_data = file.read()
    return binary_data

def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()
    columns_chatbots = [col['name'] for col in inspector.get_columns('chatbots')]

    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('username', sa.String, nullable=False),
        )
        op.execute(sa.text("INSERT INTO users (username) VALUES ('User')"))
    else:
        print("Table 'users' already exists, skipping create.")

    if 'username' in columns_chatbots:
        op.drop_column('chatbots', 'username')
    else:
        print("Column 'username' not found in 'chatbots', skipping drop.")

def downgrade():
    try:
        op.add_column('chatbots', sa.Column('username', sa.String, nullable=True))
    except Exception as e:
        print(f"Column already exists: {e}")

    try:
        op.drop_table('users')
    except Exception as e:
        print(f"Table already dropped: {e}")
    # ### end Alembic commands ###
