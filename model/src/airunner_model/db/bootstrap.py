"""Bootstrap helpers for seeding core AIRunner database tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from airunner_model.bootstrap.controlnet_bootstrap_data import (
    controlnet_bootstrap_data,
)
from airunner_services.contract_enums import Scheduler
from airunner_services.contract_enums import SignalCode
from airunner_services.bootstrap.font_settings_bootstrap_data import (
    font_settings_bootstrap_data,
)
from airunner_services.bootstrap.imagefilter_bootstrap_data import (
    imagefilter_bootstrap_data,
)
from airunner_services.bootstrap.model_bootstrap_data import (
    model_bootstrap_data,
)
from airunner_services.bootstrap.pipeline_bootstrap_data import (
    pipeline_bootstrap_data,
)
from airunner_services.bootstrap.prompt_templates_bootstrap_data import (
    prompt_templates_bootstrap_data,
)
from airunner_model.models.ai_models import AIModels
from airunner_model.models.controlnet_model import (
    ControlnetModel,
)
from airunner_model.models.font_setting import FontSetting
from airunner_model.models.pipeline_model import PipelineModel
from airunner_model.models.prompt_template import PromptTemplate
from airunner_model.models.schedulers import Schedulers
from airunner_model.models.shortcut_keys import ShortcutKeys


# Persist the existing Qt shortcut values without importing PySide6 here.
_KEY_F1 = 16777264
_KEY_F5 = 16777268
_KEY_B = 66
_KEY_E = 69
_KEY_I = 73
_KEY_Q = 81
_KEY_V = 86
_KEY_Y = 89
_KEY_Z = 90
_NO_MODIFIER = 0
_SHIFT_MODIFIER = 33554432
_CONTROL_MODIFIER = 67108864


def _bulk_insert_rows(table, rows) -> None:
    """Insert several rows into one mapped table."""
    op.bulk_insert(table, list(rows))


def set_default_ai_models() -> None:
    """Seed one default set of built-in AI model rows."""
    _bulk_insert_rows(AIModels.__table__, model_bootstrap_data)


def set_default_schedulers() -> None:
    """Seed the built-in image scheduler rows."""
    _bulk_insert_rows(Schedulers.__table__, _scheduler_rows())


def _scheduler_rows() -> list[dict[str, str]]:
    """Return the built-in scheduler seed rows."""
    return [
        _scheduler_row(Scheduler.EULER_ANCESTRAL, "EulerAncestralDiscreteScheduler"),
        _scheduler_row(Scheduler.EULER, "EulerDiscreteScheduler"),
        _scheduler_row(Scheduler.LMS, "LMSDiscreteScheduler"),
        _scheduler_row(Scheduler.HEUN, "HeunDiscreteScheduler"),
        _scheduler_row(Scheduler.DPM2, "DPMSolverSinglestepScheduler"),
        _scheduler_row(Scheduler.DPM_PP_2M, "DPMSolverMultistepScheduler"),
        _scheduler_row(Scheduler.DPM2_K, "KDPM2DiscreteScheduler"),
        _scheduler_row(Scheduler.DPM2_A_K, "KDPM2AncestralDiscreteScheduler"),
        _scheduler_row(Scheduler.DPM_PP_2M_K, "DPMSolverMultistepScheduler"),
        _scheduler_row(Scheduler.DPM_PP_2M_SDE_K, "DPMSolverMultistepScheduler"),
        _scheduler_row(Scheduler.DDIM, "DDIMScheduler"),
        _scheduler_row(Scheduler.UNIPC, "UniPCMultistepScheduler"),
        _scheduler_row(Scheduler.DDPM, "DDPMScheduler"),
        _scheduler_row(Scheduler.DEIS, "DEISMultistepScheduler"),
        _scheduler_row(Scheduler.DPM_2M_SDE_K, "DPMSolverMultistepScheduler"),
        _scheduler_row(Scheduler.PLMS, "PNDMScheduler"),
        _scheduler_row(Scheduler.DPM, "DPMSolverMultistepScheduler"),
        _scheduler_row(Scheduler.FLOW_MATCH_EULER, "FlowMatchEulerDiscreteScheduler"),
        _scheduler_row(Scheduler.FLOW_MATCH_LCM, "FlowMatchLCMScheduler"),
    ]


def _scheduler_row(scheduler: Scheduler, name: str) -> dict[str, str]:
    """Return one scheduler seed row."""
    return {"display_name": scheduler.value, "name": name}


def set_default_shortcut_keys() -> None:
    """Seed the built-in keyboard shortcut rows."""
    _bulk_insert_rows(ShortcutKeys.__table__, _shortcut_key_rows())


def _shortcut_key_rows() -> list[dict[str, object]]:
    """Return the built-in shortcut seed rows."""
    return [
        _shortcut_row(
            display_name="Generate Image",
            text="F1",
            key=_KEY_F1,
            modifiers=_NO_MODIFIER,
            description=(
                "Generate key. Responsible for triggering the generation "
                "of a Stable Diffusion image."
            ),
            signal=SignalCode.SD_GENERATE_IMAGE_SIGNAL.value,
        ),
        _shortcut_row(
            display_name="Brush Tool",
            text="B",
            key=_KEY_B,
            modifiers=_NO_MODIFIER,
            description=(
                "Brush tool key. Responsible for selecting the brush tool."
            ),
            signal=SignalCode.ENABLE_BRUSH_TOOL_SIGNAL.value,
        ),
        _shortcut_row(
            display_name="Eraser Tool",
            text="E",
            key=_KEY_E,
            modifiers=_NO_MODIFIER,
            description=(
                "Eraser tool key. Responsible for selecting the eraser "
                "tool."
            ),
            signal=SignalCode.ENABLE_ERASER_TOOL_SIGNAL.value,
        ),
        _shortcut_row(
            display_name="Move Tool",
            text="V",
            key=_KEY_V,
            modifiers=_NO_MODIFIER,
            description=(
                "Move tool key. Responsible for selecting the move tool."
            ),
            signal=SignalCode.ENABLE_MOVE_TOOL_SIGNAL.value,
        ),
        _shortcut_row(
            display_name="Undo",
            text="Ctrl+Z",
            key=_KEY_Z,
            modifiers=_CONTROL_MODIFIER,
            description="Undo the last canvas edit.",
            signal=SignalCode.UNDO_SIGNAL.value,
        ),
        _shortcut_row(
            display_name="Redo",
            text="Ctrl+Y",
            key=_KEY_Y,
            modifiers=_CONTROL_MODIFIER,
            description="Redo the last undone canvas edit.",
            signal=SignalCode.REDO_SIGNAL.value,
        ),
        _shortcut_row(
            display_name="Interrupt",
            text="Shift+Ctrl+I",
            key=_KEY_I,
            modifiers=(
                _SHIFT_MODIFIER | _CONTROL_MODIFIER
            ),
            description=(
                "Interrupt key. Responsible for interrupting the current "
                "process."
            ),
            signal=SignalCode.INTERRUPT_PROCESS_SIGNAL.value,
        ),
        _shortcut_row(
            display_name="Quit",
            text="Ctrl+Q",
            key=_KEY_Q,
            modifiers=_CONTROL_MODIFIER,
            description=(
                "Quit key. Responsible for quitting the application."
            ),
            signal=SignalCode.QUIT_APPLICATION.value,
        ),
        _shortcut_row(
            display_name="Refresh Stylesheet",
            text="F5",
            key=_KEY_F5,
            modifiers=_NO_MODIFIER,
            description=(
                "Refresh the stylesheet. Useful when creating a template."
            ),
            signal=SignalCode.REFRESH_STYLESHEET_SIGNAL.value,
        ),
    ]


def _shortcut_row(**kwargs) -> dict[str, object]:
    """Return one shortcut seed row."""
    return kwargs


def set_default_prompt_templates() -> None:
    """Seed the default prompt template rows."""
    _bulk_insert_rows(PromptTemplate.__table__, prompt_templates_bootstrap_data)


def set_default_controlnet_models() -> None:
    """Seed the default ControlNet model rows."""
    _bulk_insert_rows(ControlnetModel.__table__, controlnet_bootstrap_data)


def set_default_font_settings() -> None:
    """Seed the default font settings rows."""
    _bulk_insert_rows(FontSetting.__table__, font_settings_bootstrap_data)


def set_default_pipeline_values() -> None:
    """Seed the default pipeline model rows."""
    _bulk_insert_rows(PipelineModel.__table__, pipeline_bootstrap_data)


def set_image_filter_settings() -> None:
    """Seed image filter rows and their parameter metadata."""
    connection = op.get_bind()
    dialect_name = getattr(getattr(connection, "dialect", None), "name", "")
    for filter_data in imagefilter_bootstrap_data.values():
        existing_filter = _existing_image_filter(connection, filter_data["name"])
        if existing_filter:
            continue
        filter_id = _insert_image_filter(connection, dialect_name, filter_data)
        _insert_image_filter_values(connection, filter_id, filter_data)


def _existing_image_filter(connection, name: str):
    """Return one existing image-filter row when it already exists."""
    return connection.execute(
        sa.text("SELECT id FROM image_filter_settings WHERE name = :name"),
        {"name": name},
    ).fetchone()


def _insert_image_filter(connection, dialect_name: str, filter_data: dict) -> int:
    """Insert one image filter row and return its new identifier."""
    insert_params = {
        "name": filter_data["name"],
        "display_name": filter_data["display_name"],
        "auto_apply": filter_data["auto_apply"],
        "filter_class": filter_data["filter_class"],
    }
    if dialect_name == "postgresql":
        result = connection.execute(
            sa.text(
                "INSERT INTO image_filter_settings "
                "(name, display_name, auto_apply, filter_class) "
                "VALUES (:name, :display_name, :auto_apply, :filter_class) "
                "RETURNING id"
            ),
            insert_params,
        )
        return int(result.scalar_one())

    result = connection.execute(
        sa.text(
            "INSERT INTO image_filter_settings "
            "(name, display_name, auto_apply, filter_class) "
            "VALUES (:name, :display_name, :auto_apply, :filter_class)"
        ),
        insert_params,
    )
    return int(result.lastrowid)


def _insert_image_filter_values(
    connection,
    filter_id: int,
    filter_data: dict,
) -> None:
    """Insert the parameter rows for one seeded image filter."""
    for value_data in filter_data["image_filter_values"].values():
        connection.execute(
            sa.text(
                "INSERT INTO image_filter_values "
                "(name, value, value_type, min_value, max_value, image_filter_id) "
                "VALUES (:name, :value, :value_type, :min_value, :max_value, :image_filter_id)"
            ),
            {
                "name": value_data["name"],
                "value": value_data["value"],
                "value_type": value_data["value_type"],
                "min_value": value_data["min_value"],
                "max_value": value_data["max_value"],
                "image_filter_id": filter_id,
            },
        )


__all__ = [
    "set_default_ai_models",
    "set_default_controlnet_models",
    "set_default_font_settings",
    "set_default_pipeline_values",
    "set_default_prompt_templates",
    "set_default_schedulers",
    "set_default_shortcut_keys",
    "set_image_filter_settings",
]
