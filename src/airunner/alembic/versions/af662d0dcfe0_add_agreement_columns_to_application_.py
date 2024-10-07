"""Add agreement columns to application_settings

Revision ID: af662d0dcfe0
Revises: c8103d0c7d77
Create Date: 2024-10-07 06:07:54.680019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'af662d0dcfe0'
down_revision: Union[str, None] = 'c8103d0c7d77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('application_settings')]

    if 'stable_diffusion_agreement_checked' not in columns:
        op.add_column('application_settings', sa.Column('stable_diffusion_agreement_checked', sa.Boolean, default=True))
    if 'airunner_agreement_checked' not in columns:
        op.add_column('application_settings', sa.Column('airunner_agreement_checked', sa.Boolean, default=True))
    if 'user_agreement_checked' not in columns:
        op.add_column('application_settings', sa.Column('user_agreement_checked', sa.Boolean, default=True))
    if 'llama_license_agreement_checked' not in columns:
        op.add_column('application_settings', sa.Column('llama_license_agreement_checked', sa.Boolean, default=True))

def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('application_settings')]

    if 'stable_diffusion_agreement_checked' in columns:
        op.drop_column('application_settings', 'stable_diffusion_agreement_checked')
    if 'airunner_agreement_checked' in columns:
        op.drop_column('application_settings', 'airunner_agreement_checked')
    if 'user_agreement_checked' in columns:
        op.drop_column('application_settings', 'user_agreement_checked')
    if 'llama_license_agreement_checked' in columns:
        op.drop_column('application_settings', 'llama_license_agreement_checked')
    # ### end Alembic commands ###
