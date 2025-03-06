"""Create whisper_settings table

Revision ID: 536e18463461
Revises: 3212e8fccc68
Create Date: 2024-10-13 09:34:20.974389

"""
from typing import Union
from alembic import op
from airunner.utils.db.table import table_exists
from airunner.data.models import WhisperSettings

revision: str = '536e18463461'
down_revision: Union[str, None] = '3212e8fccc68'

def set_default_values(model_name_):
    default_values = {}
    for column in model_name_.__table__.columns:
        if column.default is not None:
            default_values[column.name] = column.default.arg
    op.bulk_insert(
        model_name_.__table__,
        [default_values]
    )

def upgrade():
    if not table_exists(WhisperSettings.__tablename__):
        try:
            op.create_table(
                WhisperSettings.__tablename__,
                *WhisperSettings.__table__.columns
            )
        except Exception as e:
            print("Failed to create table", str(e))

        try:
            set_default_values(WhisperSettings)
        except Exception as e:
            print("Failed to set default values", str(e))
    else:
        print("whisper_settings already exists, skipping")

def downgrade():
    if table_exists(WhisperSettings.__tablename__):
        try:
            op.drop_table('whisper_settings')
        except Exception as e:
            print("Failed to drop table", str(e))
