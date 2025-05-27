"""
Tests for airunner.utils.db.bootstrap
Covers all public functions, error handling, and edge cases.
All DB/model/engine dependencies are mocked. No real DB is touched.
"""

import pytest
from unittest.mock import patch, MagicMock
import airunner.utils.db.bootstrap as dbboot


# Patch all model/data imports and op for all tests
def patch_all():
    table_mock = MagicMock()
    return patch.multiple(
        "airunner.utils.db.bootstrap",
        op=MagicMock(),
        AIModels=MagicMock(__table__=table_mock),
        Schedulers=MagicMock(__table__=table_mock),
        ShortcutKeys=MagicMock(__table__=table_mock),
        PromptTemplate=MagicMock(__table__=table_mock),
        ControlnetModel=MagicMock(__table__=table_mock),
        FontSetting=MagicMock(__table__=table_mock),
        PipelineModel=MagicMock(__table__=table_mock),
        controlnet_bootstrap_data=[{"foo": 1}],
        font_settings_bootstrap_data=[{"bar": 2}],
        imagefilter_bootstrap_data={
            "filt": {
                "name": "filt",
                "display_name": "filt",
                "auto_apply": True,
                "filter_class": "F",
                "image_filter_values": {
                    "val": {
                        "name": "val",
                        "value": 1,
                        "value_type": "int",
                        "min_value": 0,
                        "max_value": 2,
                    }
                },
            }
        },
        model_bootstrap_data=[{"baz": 3}],
        pipeline_bootstrap_data=[{"pipe": 4}],
        prompt_templates_bootstrap_data=[{"tmpl": 5}],
        SignalCode=MagicMock(),
        Scheduler=MagicMock(
            EULER_ANCESTRAL=MagicMock(value="EA"),
            EULER=MagicMock(value="E"),
            LMS=MagicMock(value="L"),
            HEUN=MagicMock(value="H"),
            DPM2=MagicMock(value="D2"),
            DPM_PP_2M=MagicMock(value="DPP2M"),
            DPM2_K=MagicMock(value="D2K"),
            DPM2_A_K=MagicMock(value="D2AK"),
            DPM_PP_2M_K=MagicMock(value="DPP2MK"),
            DPM_PP_2M_SDE_K=MagicMock(value="DPP2MSDEK"),
            DDIM=MagicMock(value="DDIM"),
            UNIPC=MagicMock(value="UNIPC"),
            DDPM=MagicMock(value="DDPM"),
            DEIS=MagicMock(value="DEIS"),
            DPM_2M_SDE_K=MagicMock(value="DPM2MSDEK"),
            PLMS=MagicMock(value="PLMS"),
            DPM=MagicMock(value="DPM"),
        ),
        return_dict=True,
    )


def test_set_default_ai_models():
    with patch("airunner.utils.db.bootstrap.op") as op_mock, patch(
        "airunner.utils.db.bootstrap.AIModels", __table__=MagicMock()
    ):
        dbboot.set_default_ai_models()
        op_mock.bulk_insert.assert_called_once()


def test_set_default_schedulers():
    with patch("airunner.utils.db.bootstrap.op") as op_mock, patch(
        "airunner.utils.db.bootstrap.Schedulers", __table__=MagicMock()
    ), patch("airunner.utils.db.bootstrap.Scheduler"):
        dbboot.set_default_schedulers()
        op_mock.bulk_insert.assert_called_once()


def test_set_default_shortcut_keys():
    with patch("airunner.utils.db.bootstrap.op") as op_mock, patch(
        "airunner.utils.db.bootstrap.ShortcutKeys", __table__=MagicMock()
    ), patch("airunner.utils.db.bootstrap.SignalCode"), patch(
        "airunner.utils.db.bootstrap.QtCore"
    ):
        dbboot.set_default_shortcut_keys()
        op_mock.bulk_insert.assert_called_once()


def test_set_default_prompt_templates():
    with patch("airunner.utils.db.bootstrap.op") as op_mock, patch(
        "airunner.utils.db.bootstrap.PromptTemplate", __table__=MagicMock()
    ), patch(
        "airunner.utils.db.bootstrap.prompt_templates_bootstrap_data",
        [{"tmpl": 5}],
    ):
        dbboot.set_default_prompt_templates()
        op_mock.bulk_insert.assert_called_once()


def test_set_default_controlnet_models():
    with patch("airunner.utils.db.bootstrap.op") as op_mock, patch(
        "airunner.utils.db.bootstrap.ControlnetModel", __table__=MagicMock()
    ), patch("airunner.utils.db.bootstrap.controlnet_bootstrap_data", [{"foo": 1}]):
        dbboot.set_default_controlnet_models()
        op_mock.bulk_insert.assert_called_once()


def test_set_default_font_settings():
    with patch("airunner.utils.db.bootstrap.op") as op_mock, patch(
        "airunner.utils.db.bootstrap.FontSetting", __table__=MagicMock()
    ), patch(
        "airunner.utils.db.bootstrap.font_settings_bootstrap_data",
        [{"bar": 2}],
    ):
        dbboot.set_default_font_settings()
        assert op_mock.bulk_insert.call_count == 1


def test_set_default_pipeline_values():
    with patch("airunner.utils.db.bootstrap.op") as op_mock, patch(
        "airunner.utils.db.bootstrap.PipelineModel", __table__=MagicMock()
    ), patch("airunner.utils.db.bootstrap.pipeline_bootstrap_data", [{"pipe": 4}]):
        dbboot.set_default_pipeline_values()
        assert op_mock.bulk_insert.call_count == 1


def test_set_image_filter_settings():
    with patch("airunner.utils.db.bootstrap.op") as op_mock, patch(
        "airunner.utils.db.bootstrap.imagefilter_bootstrap_data",
        {
            "filt": {
                "name": "filt",
                "display_name": "filt",
                "auto_apply": True,
                "filter_class": "F",
                "image_filter_values": {
                    "val": {
                        "name": "val",
                        "value": 1,
                        "value_type": "int",
                        "min_value": 0,
                        "max_value": 2,
                    }
                },
            }
        },
    ):
        conn = MagicMock()
        op_mock.get_bind.return_value = conn
        result = MagicMock()
        result.lastrowid = 99
        conn.execute.side_effect = [result, None]
        dbboot.set_image_filter_settings()
        assert conn.execute.call_count == 2
