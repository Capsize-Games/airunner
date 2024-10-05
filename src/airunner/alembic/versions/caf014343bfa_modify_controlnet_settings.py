from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'caf014343bfa'
down_revision = 'a80df33d1539'
branch_labels = None
depends_on = None

def upgrade():
    # Drop controlnet_image_settings table if it exists
    op.execute('DROP TABLE IF EXISTS controlnet_image_settings')

    # Get the connection and inspector
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # Get existing columns in controlnet_settings table
    existing_columns = [col['name'] for col in inspector.get_columns('controlnet_settings')]

    # Add columns to controlnet_settings table if they don't already exist
    with op.batch_alter_table('controlnet_settings') as batch_op:
        if 'generated_image' not in existing_columns:
            batch_op.add_column(sa.Column('generated_image', sa.String, nullable=True))
        if 'controlnet' not in existing_columns:
            batch_op.add_column(sa.Column('controlnet', sa.String, default='canny'))
        if 'guidance_scale' not in existing_columns:
            batch_op.add_column(sa.Column('guidance_scale', sa.Integer, default=750))

def downgrade():
    # Remove columns from controlnet_settings table if they exist
    with op.batch_alter_table('controlnet_settings') as batch_op:
        batch_op.drop_column('generated_image')
        batch_op.drop_column('controlnet')
        batch_op.drop_column('guidance_scale')

    # Recreate controlnet_image_settings table
    op.create_table(
        'controlnet_image_settings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        # Add other columns as needed
    )
