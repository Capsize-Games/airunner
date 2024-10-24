"""Change image and mask columns to BLOB

Revision ID: 26a0d29a3af3
Revises: f403ff7468e8
Create Date: 2024-10-24 12:31:37.706170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '26a0d29a3af3'
down_revision: Union[str, None] = 'f403ff7468e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    try:
        op.alter_column('controlnet_settings', 'image', type_=sa.LargeBinary, existing_type=sa.String, nullable=True)
        op.alter_column('controlnet_settings', 'generated_image', type_=sa.LargeBinary, existing_type=sa.String, nullable=True)
    except sa.exc.OperationalError:
        pass

    try:
        op.alter_column('image_to_image_settings', 'image', type_=sa.LargeBinary, existing_type=sa.String, nullable=True)
    except sa.exc.OperationalError:
        pass

    try:
        op.alter_column('outpaint_settings', 'image', type_=sa.LargeBinary, existing_type=sa.String, nullable=True)
    except sa.exc.OperationalError:
        pass

    try:
        op.alter_column('drawing_pad_settings', 'image', type_=sa.LargeBinary, existing_type=sa.String, nullable=True)
        op.alter_column('drawing_pad_settings', 'mask', type_=sa.LargeBinary, existing_type=sa.String, nullable=True)
    except sa.exc.OperationalError:
        pass


def downgrade():
    try:
        op.alter_column('controlnet_settings', 'image', type_=sa.String, existing_type=sa.LargeBinary, nullable=True)
        op.alter_column('controlnet_settings', 'generated_image', type_=sa.String, existing_type=sa.LargeBinary, nullable=True)
    except sa.exc.OperationalError:
        pass

    try:
        op.alter_column('image_to_image_settings', 'image', type_=sa.String, existing_type=sa.LargeBinary, nullable=True)
    except sa.exc.OperationalError:
        pass

    try:
        op.alter_column('outpaint_settings', 'image', type_=sa.String, existing_type=sa.LargeBinary, nullable=True)
    except sa.exc.OperationalError:
        pass

    try:
        op.alter_column('drawing_pad_settings', 'image', type_=sa.String, existing_type=sa.LargeBinary, nullable=True)
        op.alter_column('drawing_pad_settings', 'mask', type_=sa.String, existing_type=sa.LargeBinary, nullable=True)
    except sa.exc.OperationalError:
        pass
