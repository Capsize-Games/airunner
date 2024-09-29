"""Create window_settings table

Revision ID: 1d40f74da876
Revises: 1ee2a000c0d1
Create Date: 2024-09-28 20:09:34.525929

"""
from typing import Sequence, Union

import sqlalchemy
from alembic import op

from airunner.aihandler.models import settings_models

# revision identifiers, used by Alembic.
revision: str = '1d40f74da876'
down_revision: Union[str, None] = '1ee2a000c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(settings_models.WindowSettings.__tablename__,
                    *settings_models.WindowSettings.__table__.columns)
    default_values = {}
    for column in settings_models.WindowSettings.__table__.columns:
        if column.default is not None:
            default_values[column.name] = column.default.arg
    op.bulk_insert(
        settings_models.WindowSettings.__table__,
        [default_values]
    )

def downgrade():
    try:
        op.drop_table(settings_models.WindowSettings.__tablename__)
    except sqlalchemy.exc.OperationalError:
        pass
    # ### end Alembic commands ###
