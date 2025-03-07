"""Modify default stt and tts paths

Revision ID: 7fb526dc074c
Revises: 181e31f78151
Create Date: 2025-03-07 12:14:52.042949

"""
from typing import Union
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text  # Add import for text()

from airunner.settings import BASE_PATH
from airunner.data.models.path_settings import PathSettings
from airunner.utils.db import safe_alter_column

revision: str = '7fb526dc074c'
down_revision: Union[str, None] = '181e31f78151'


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_path_settings")

    stt_model_path = os.path.expanduser(os.path.join(BASE_PATH, "text", "models", "stt"))
    tts_model_path = os.path.expanduser(os.path.join(BASE_PATH, "text", "models", "tts"))
    safe_alter_column(
        PathSettings,
        "stt_model_path",
        existing_type=sa.String(),
        nullable=True,
        existing_server_default=stt_model_path
    )
    safe_alter_column(
        PathSettings,
        "tts_model_path",
        existing_type=sa.String(),
        nullable=True,
        existing_server_default=tts_model_path
    )
    update_path_values(stt_model_path, tts_model_path)


def downgrade() -> None:
    stt_model_path = os.path.expanduser(os.path.join(BASE_PATH, "text", "models", "stt", "models"))
    tts_model_path = os.path.expanduser(os.path.join(BASE_PATH, "text", "models", "tts", "models"))
    safe_alter_column(
        PathSettings,
        "stt_model_path",
        existing_type=sa.String(),
        nullable=True,
        existing_server_default=stt_model_path
    )
    safe_alter_column(
        PathSettings,
        "tts_model_path",
        existing_type=sa.String(),
        nullable=True,
        existing_server_default=tts_model_path
    )
    update_path_values(stt_model_path, tts_model_path)


def update_path_values(stt_model_path, tts_model_path):
    connection = op.get_bind()
    
    # Get all path settings
    result = connection.execute(text("SELECT id, base_path FROM path_settings"))
    path_settings = result.fetchall()
    
    for path_setting in path_settings:
        path_id = path_setting[0]
        base_path = path_setting[1]

        stt_model_path = stt_model_path.replace(os.path.expanduser(BASE_PATH), base_path)
        tts_model_path = tts_model_path.replace(os.path.expanduser(BASE_PATH), base_path)
        
        try:
            connection.execute(
                text("UPDATE path_settings SET stt_model_path = :stt, tts_model_path = :tts WHERE id = :id"),
                {"stt": stt_model_path, "tts": tts_model_path, "id": path_id}
            )
            print(f"Successfully updated path_settings with ID {path_id}")
        except Exception as e:
            print(f"Error updating path_settings with ID {path_id}: {str(e)}")
            raise
