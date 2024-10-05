from alembic import op
import sqlalchemy as sa
from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data

# revision identifiers, used by Alembic.
revision = 'a80df33d1539'
down_revision = 'b63bd35f72b0'
branch_labels = None
depends_on = None

def upgrade():
    # Check if the 'version' column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('controlnet_models')]

    if 'version' not in columns:
        # Determine the default value based on controlnet_bootstrap_data
        default_value = 'SD 1.5'
        for item in controlnet_bootstrap_data:
            if item['display_name'] in columns:
                default_value = item['display_name']
                break

        # Add the 'version' column with the determined default value
        op.add_column('controlnet_models', sa.Column('version', sa.String(), nullable=False, server_default=default_value))

def downgrade():
    # Drop the 'version' column if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('controlnet_models')]

    if 'version' in columns:
        op.drop_column('controlnet_models', 'version')
    # ### end Alembic commands ###
