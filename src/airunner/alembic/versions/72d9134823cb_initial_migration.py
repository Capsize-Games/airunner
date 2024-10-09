"""Initial migration

Revision ID: 72d9134823cb
Revises: 
Create Date: 2024-10-07 17:18:54.617216

"""
from typing import Sequence, Union

import sqlalchemy
from alembic import op
import sqlalchemy as sa

from airunner.data.models import settings_models
from airunner.data.models.settings_models import Base
from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.font_settings_bootstrap_data import font_settings_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.data.bootstrap.prompt_templates_bootstrap_data import prompt_templates_bootstrap_data
from airunner.settings import SCHEDULER_CLASSES, DEFAULT_SHORTCUTS

# revision identifiers, used by Alembic.
revision: str = '72d9134823cb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get all model classes
    models = Base.__subclasses__()

    # Iterate over each model
    for model in models:
        op.create_table(
            model.__tablename__,
            *model.__table__.columns
        )
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
    # ### end Alembic commands ###


def set_default_values(model_name_):
    default_values = {}
    for column in model_name_.__table__.columns:
        if column.default is not None:
            default_values[column.name] = column.default.arg
    op.bulk_insert(
        model_name_.__table__,
        [default_values]
    )

def set_default_ai_models():
    values = []
    for model in model_bootstrap_data:
        values.append(model)
    op.bulk_insert(
        settings_models.AIModels.__table__,
        values
    )

def set_default_schedulers():
    op.bulk_insert(
        settings_models.Schedulers.__table__,
        SCHEDULER_CLASSES
    )

def set_default_shortcut_keys():
    op.bulk_insert(
        settings_models.ShortcutKeys.__table__,
        DEFAULT_SHORTCUTS
    )

def set_default_prompt_templates():
    values = []
    for template in prompt_templates_bootstrap_data:
        values.append(template)
    op.bulk_insert(
        settings_models.PromptTemplate.__table__,
        values
    )

def set_default_controlnet_models():
    values = []
    for template in controlnet_bootstrap_data:
        values.append(template)
    op.bulk_insert(
        settings_models.ControlnetModel.__table__,
        values
    )

def set_default_font_settings():
    for font_setting in font_settings_bootstrap_data:
        op.bulk_insert(
            settings_models.FontSetting.__table__,
            [font_setting]
        )

def set_default_pipeline_values():
    for pipeline in pipeline_bootstrap_data:
        op.bulk_insert(
            settings_models.PipelineModel.__table__,
            [pipeline]
        )

def set_image_filter_settings():
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

def downgrade() -> None:
    models = Base.__subclasses__()
    for model in models:
        try:
            op.drop_table(model.__tablename__)
        except sqlalchemy.exc.OperationalError:
            pass
        set_default_values(model)
    # ### end Alembic commands ###
