"""drop controlnet_enabled column from application_settings

Revision ID: 7e744b48e075
Revises: c4fb749c3e22
Create Date: 2024-10-03 04:19:35.571484

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7e744b48e075'
down_revision: Union[str, None] = 'c4fb749c3e22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the controlnet_enabled column from application_settings
    with op.batch_alter_table('application_settings') as batch_op:
        batch_op.drop_column('controlnet_enabled')


def downgrade() -> None:
    # Add the controlnet_enabled column back to application_settings
    with op.batch_alter_table('application_settings') as batch_op:
        batch_op.add_column(sa.Column('controlnet_enabled', sa.Boolean, default=False))
