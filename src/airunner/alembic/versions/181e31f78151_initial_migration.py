"""Initial migration

Revision ID: 181e31f78151
Revises: None
Create Date: 2025-03-06 19:37:44.523586

"""
from typing import Sequence, Union

from alembic import op
from airunner.data import models
from airunner.utils.db.bootstrap import (
    set_default_ai_models,
    set_default_schedulers,
    set_default_shortcut_keys,
    set_default_prompt_templates,
    set_default_controlnet_models,
    set_default_font_settings,
    set_default_pipeline_values,
    set_image_filter_settings,
)


# revision identifiers, used by Alembic.
revision: str = '181e31f78151'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tables using models
    models.Base.metadata.create_all(bind=op.get_bind())
    set_default_ai_models()
    set_default_schedulers()
    set_default_shortcut_keys()
    set_default_prompt_templates()
    set_default_controlnet_models()
    set_default_font_settings()
    set_default_pipeline_values()
    set_image_filter_settings()


def downgrade() -> None:
    # Drop tables using models
    models.Base.metadata.drop_all(bind=op.get_bind())