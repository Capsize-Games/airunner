"""Initial migration

Revision ID: 72d9134823cb
Revises: 
Create Date: 2024-10-07 17:18:54.617216

"""
from typing import Union

from alembic import op

from airunner.data.models.base import BaseModel
from airunner.utils.db import add_tables, drop_tables
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
revision: str = '72d9134823cb'
down_revision: Union[str, None] = None


def upgrade() -> None:
    # Get all model classes
    models = BaseModel.__subclasses__()

    add_tables(models)

    # Iterate over each model
    for model in models:
        if not model.__tablename__ in (
            "shortcut_keys",
            "lora",
            "embeddings",
            "prompt_templates",
            "aimodels",
            "schedulers",
            "controlnet_models",
            "font_settings",
            "pipeline_models",
            "messages",
            "summaries",
            "image_filter_settings",
            "image_filter_values",
            "conversations",
            "saved_prompts",
            "target_directories",
            "target_files",
        ):
            try:
                set_default_values(model)
            except Exception as e:
                print(e)

    set_default_ai_models()
    set_default_schedulers()
    set_default_shortcut_keys()
    set_default_prompt_templates()
    set_default_controlnet_models()
    set_default_font_settings()
    set_default_pipeline_values()
    set_image_filter_settings()


def set_default_values(model_name_):
    default_values = {}
    for column in model_name_.__table__.columns:
        if column.default is not None:
            default_values[column.name] = column.default.arg

    # Handle the 'users' table specifically to avoid the NotNullViolation error
    if model_name_.__tablename__ == 'users':
        # Provide a default username to satisfy the NOT NULL constraint
        default_values['username'] = 'default_user'

    op.bulk_insert(
        model_name_.__table__,
        [default_values]
    )

def downgrade() -> None:
    drop_tables(BaseModel.__subclasses__())
