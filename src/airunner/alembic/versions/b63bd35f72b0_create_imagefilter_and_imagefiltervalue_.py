from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data

# revision identifiers, used by Alembic.
revision = 'b63bd35f72b0'
down_revision = 'f4d8b6e9a1e8'
branch_labels = None
depends_on = None

def upgrade():
    # Create ImageFilter table
    op.create_table(
        'image_filter_settings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('display_name', sa.String, nullable=False),
        sa.Column('auto_apply', sa.Boolean, default=False),
        sa.Column('filter_class', sa.String, nullable=False)
    )

    # Create ImageFilterValue table
    op.create_table(
        'image_filter_values',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('value', sa.String, nullable=False),
        sa.Column('value_type', sa.String, nullable=False),
        sa.Column('min_value', sa.Float, nullable=True),
        sa.Column('max_value', sa.Float, nullable=True),
        sa.Column('image_filter_id', sa.Integer, sa.ForeignKey('image_filter_settings.id'))
    )

    # Insert default data
    connection = op.get_bind()
    for filter_name, filter_data in imagefilter_bootstrap_data.items():
        result = connection.execute(
            sa.text(
                "INSERT INTO image_filter_settings (name, display_name, auto_apply, filter_class) "
                "VALUES (:name, :display_name, :auto_apply, :filter_class)"
            ),
            {
                'name': filter_data['name'],
                'display_name': filter_data['display_name'],
                'auto_apply': filter_data['auto_apply'],
                'filter_class': filter_data['filter_class']
            }
        )
        filter_id = result.lastrowid
        for value_name, value_data in filter_data['image_filter_values'].items():
            connection.execute(
                sa.text(
                    "INSERT INTO image_filter_values (name, value, value_type, min_value, max_value, image_filter_id) "
                    "VALUES (:name, :value, :value_type, :min_value, :max_value, :image_filter_id)"
                ),
                {
                    'name': value_data['name'],
                    'value': value_data['value'],
                    'value_type': value_data['value_type'],
                    'min_value': value_data['min_value'],
                    'max_value': value_data['max_value'],
                    'image_filter_id': filter_id
                }
            )

def downgrade():
    # Drop ImageFilterValue table
    op.drop_table('image_filter_values')

    # Drop ImageFilter table
    op.drop_table('image_filter_settings')
