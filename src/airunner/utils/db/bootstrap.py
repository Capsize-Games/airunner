from alembic import op
import sqlalchemy as sa

from PySide6 import QtCore

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
from airunner.enums import SignalCode, Scheduler


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
        [
            dict(
                display_name=Scheduler.EULER_ANCESTRAL.value,
                name="EulerAncestralDiscreteScheduler",
            ),
            dict(
                display_name=Scheduler.EULER.value,
                name="EulerDiscreteScheduler",
            ),
            dict(
                display_name=Scheduler.LMS.value,
                name="LMSDiscreteScheduler",
            ),
            dict(
                display_name=Scheduler.HEUN.value,
                name="HeunDiscreteScheduler",
            ),
            dict(
                display_name=Scheduler.DPM2.value,
                name="DPMSolverSinglestepScheduler",
            ),
            dict(
                display_name=Scheduler.DPM_PP_2M.value,
                name="DPMSolverMultistepScheduler",
            ),
            dict(
                display_name=Scheduler.DPM2_K.value,
                name="KDPM2DiscreteScheduler",
            ),
            dict(
                display_name=Scheduler.DPM2_A_K.value,
                name="KDPM2AncestralDiscreteScheduler",
            ),
            dict(
                display_name=Scheduler.DPM_PP_2M_K.value,
                name="DPMSolverMultistepScheduler",
            ),
            dict(
                display_name=Scheduler.DPM_PP_2M_SDE_K.value,
                name="DPMSolverMultistepScheduler",
            ),
            dict(
                display_name=Scheduler.DDIM.value,
                name="DDIMScheduler",
            ),
            dict(
                display_name=Scheduler.UNIPC.value,
                name="UniPCMultistepScheduler",
            ),
            dict(
                display_name=Scheduler.DDPM.value,
                name="DDPMScheduler",
            ),
            dict(
                display_name=Scheduler.DEIS.value,
                name="DEISMultistepScheduler",
            ),
            dict(
                display_name=Scheduler.DPM_2M_SDE_K.value,
                name="DPMSolverMultistepScheduler",
            ),
            dict(
                display_name=Scheduler.PLMS.value,
                name="PNDMScheduler",
            ),
            dict(
                display_name=Scheduler.DPM.value,
                name="DPMSolverMultistepScheduler",
            ),
        ]
    )


def set_default_shortcut_keys():
    op.bulk_insert(
        ShortcutKeys.__table__,
        [
            {
                "display_name": "Generate Image",
                "text": "F1",
                "key": QtCore.Qt.Key.Key_F1.value,
                "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
                "description": "Generate key. Responsible for triggering the generation of a Stable Diffusion image.",
                "signal": SignalCode.SD_GENERATE_IMAGE_SIGNAL.value
            },
            {
                "display_name": "Brush Tool",
                "text": "B",
                "key": QtCore.Qt.Key.Key_B.value,
                "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
                "description": "Brush tool key. Responsible for selecting the brush tool.",
                "signal": SignalCode.ENABLE_BRUSH_TOOL_SIGNAL.value
            },
            {
                "display_name": "Eraser Tool",
                "text": "E",
                "key": QtCore.Qt.Key.Key_E.value,
                "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
                "description": "Eraser tool key. Responsible for selecting the eraser tool.",
                "signal": SignalCode.ENABLE_ERASER_TOOL_SIGNAL.value
            },
            {
                "display_name": "Move Tool",
                "text": "V",
                "key": QtCore.Qt.Key.Key_V.value,
                "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
                "description": "Move tool key. Responsible for selecting the move tool.",
                "signal": SignalCode.ENABLE_MOVE_TOOL_SIGNAL.value
            },
            {
                "display_name": "Interrupt",
                "text": "Shift+Ctrl+I",
                "key": QtCore.Qt.Key.Key_I.value,
                "modifiers": QtCore.Qt.KeyboardModifier.ShiftModifier.value | QtCore.Qt.KeyboardModifier.ControlModifier.value,
                "description": "Interrupt key. Responsible for interrupting the current process.",
                "signal": SignalCode.INTERRUPT_PROCESS_SIGNAL.value
            },
            {
                "display_name": "Navigate",
                "text": "Shift+Ctrl+P",
                "key": QtCore.Qt.Key.Key_P.value,
                "modifiers": QtCore.Qt.KeyboardModifier.ShiftModifier.value | QtCore.Qt.KeyboardModifier.ControlModifier.value,
                "description": "URL key. Responsible for navigating to a URL.",
                "signal": SignalCode.NAVIGATE_TO_URL.value
            },
            {
                "display_name": "Quit",
                "text": "Ctrl+Q",
                "key": QtCore.Qt.Key.Key_Q.value,
                "modifiers": QtCore.Qt.KeyboardModifier.ControlModifier.value,
                "description": "Quit key. Responsible for quitting the application.",
                "signal": SignalCode.QUIT_APPLICATION.value
            },
            {
                "display_name": "Refresh Stylesheet",
                "text": "F5",
                "key": QtCore.Qt.Key.Key_F5.value,
                "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
                "description": "Refresh the stylesheet. Useful when creating a template.",
                "signal": SignalCode.REFRESH_STYLESHEET_SIGNAL.value
            },
        ]
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
