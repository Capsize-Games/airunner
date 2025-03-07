"""Consolidated base migration

Revision ID: 5d69fae414fe
Revises: 093e44cf3895
Create Date: 2025-03-06 16:48:58.012049

"""
from typing import Union

from airunner.data.models.base import BaseModel
from airunner.utils.db import add_tables
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


revision: str = '5d69fae414fe'
down_revision: Union[str, None] = None


def upgrade() -> None:
    add_tables(BaseModel.__subclasses__())
    set_default_ai_models()
    set_default_schedulers()
    set_default_shortcut_keys()
    set_default_prompt_templates()
    set_default_controlnet_models()
    set_default_font_settings()
    set_default_pipeline_values()
    set_image_filter_settings()
    

def downgrade() -> None:
    pass