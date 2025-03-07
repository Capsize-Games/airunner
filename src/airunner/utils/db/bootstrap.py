from alembic import op
import sqlalchemy as sa

from airunner.data.models import (
    AIModels,
    Schedulers,
    ShortcutKeys,
    PromptTemplate,
    ControlnetModel,
    FontSetting,
    PipelineModel
)
from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.font_settings_bootstrap_data import font_settings_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data
from airunner.data.bootstrap.prompt_templates_bootstrap_data import prompt_templates_bootstrap_data
from airunner.settings import SCHEDULER_CLASSES, DEFAULT_SHORTCUTS

def set_default_ai_models():
    values = []
    for model in model_bootstrap_data:
        values.append(model)
    op.bulk_insert(
        AIModels.__table__,
        values
    )

def set_default_schedulers():
    op.bulk_insert(
        Schedulers.__table__,
        SCHEDULER_CLASSES
    )

def set_default_shortcut_keys():
    op.bulk_insert(
        ShortcutKeys.__table__,
        DEFAULT_SHORTCUTS
    )

def set_default_prompt_templates():
    values = []
    for template in prompt_templates_bootstrap_data:
        values.append(template)
    op.bulk_insert(
        PromptTemplate.__table__,
        values
    )

def set_default_controlnet_models():
    values = []
    for template in controlnet_bootstrap_data:
        values.append(template)
    op.bulk_insert(
        ControlnetModel.__table__,
        values
    )

def set_default_font_settings():
    for font_setting in font_settings_bootstrap_data:
        op.bulk_insert(
            FontSetting.__table__,
            [font_setting]
        )

def set_default_pipeline_values():
    for pipeline in pipeline_bootstrap_data:
        op.bulk_insert(
            PipelineModel.__table__,
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