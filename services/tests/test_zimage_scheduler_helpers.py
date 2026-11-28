"""Unit tests for the Z-Image scheduler-loader helpers.

_resolve_scheduler_name, _scheduler_base_config, and
_log_loaded_scheduler were extracted to keep _load_scheduler within
the long-function threshold. These tests pin the name fallback
chain, the config sanitization, and the log content.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.art.runtime_enums import Scheduler
from airunner_services.model_management.zimage_model_manager import (
    ZImageModelManager,
)


def _make_obj():
    obj = ZImageModelManager.__new__(ZImageModelManager)
    obj.logger = MagicMock()
    obj.image_request = None
    obj._scheduler_name = None
    obj._scheduler = SimpleNamespace(
        config={"use_karras_sigmas": True, "other": 1},
        __class__=type("Sched", (), {}),
    )
    return obj


def test_resolve_name_prefers_explicit_argument():
    obj = _make_obj()
    assert (
        obj._resolve_scheduler_name(Scheduler.FLOW_MATCH_EULER.value)
        == Scheduler.FLOW_MATCH_EULER.value
    )


def test_resolve_name_falls_back_to_request_then_stored():
    obj = _make_obj()
    valid = Scheduler.FLOW_MATCH_LCM.value
    obj.image_request = SimpleNamespace(scheduler=valid)
    assert obj._resolve_scheduler_name(None) == valid
    obj.image_request = None
    obj._scheduler_name = valid
    assert obj._resolve_scheduler_name(None) == valid


def test_resolve_name_replaces_non_flow_match():
    obj = _make_obj()
    obj._resolve_scheduler_name("ddim")
    obj.logger.warning.assert_called_once()


def test_base_config_none_without_scheduler():
    assert ZImageModelManager._scheduler_base_config(None) is None


def test_base_config_none_without_config_attr():
    assert ZImageModelManager._scheduler_base_config(object()) is None


def test_base_config_strips_sampling_flags():
    current = SimpleNamespace(
        config={
            "use_karras_sigmas": True,
            "stochastic_sampling": True,
            "use_exponential_sigmas": True,
            "use_beta_sigmas": True,
            "keep": 7,
        }
    )
    out = ZImageModelManager._scheduler_base_config(current)
    assert out == {"keep": 7}


def test_log_loaded_scheduler_reports_flags():
    obj = _make_obj()
    obj._log_loaded_scheduler("flow")
    obj.logger.info.assert_called_once()
    message = obj.logger.info.call_args[0][0]
    assert "karras=True" in message


def test_log_loaded_scheduler_without_flags_has_no_suffix():
    obj = _make_obj()
    obj._scheduler = SimpleNamespace(config={})
    obj._log_loaded_scheduler("flow")
    message = obj.logger.info.call_args[0][0]
    assert "(" not in message
