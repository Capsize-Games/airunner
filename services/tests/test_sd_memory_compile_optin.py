"""Unit tests for SDMemoryManagementMixin._apply_torch_compile_opt_in.

The helper was extracted to keep _make_memory_efficient within the
long-function threshold. These tests pin the opt-in branch behavior.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.art.managers.stablediffusion.mixins.sd_memory_management_mixin import (
    SDMemoryManagementMixin,
)


def _make_obj(use_compile, applied_flag):
    obj = SDMemoryManagementMixin.__new__(SDMemoryManagementMixin)
    obj.memory_settings = SimpleNamespace(use_torch_compile=use_compile)
    obj._memory_settings_flags = {"torch_compile_applied": applied_flag}
    obj._apply_torch_compile = MagicMock(return_value=True)
    return obj


def test_enable_applies_and_flags_true():
    obj = _make_obj(True, None)
    obj._apply_torch_compile_opt_in()
    obj._apply_torch_compile.assert_called_once_with(True)
    assert obj._memory_settings_flags["torch_compile_applied"] is True


def test_enable_failed_apply_flags_none():
    obj = _make_obj(True, False)
    obj._apply_torch_compile.return_value = False
    obj._apply_torch_compile_opt_in()
    assert obj._memory_settings_flags["torch_compile_applied"] is None


def test_disable_applies_and_flags_false():
    obj = _make_obj(False, True)
    obj._apply_torch_compile_opt_in()
    obj._apply_torch_compile.assert_called_once_with(False)
    assert obj._memory_settings_flags["torch_compile_applied"] is False


def test_unchanged_setting_skips_apply():
    obj = _make_obj(True, True)
    obj._apply_torch_compile_opt_in()
    obj._apply_torch_compile.assert_not_called()


def test_missing_setting_attribute_treated_as_disabled():
    obj = _make_obj(False, None)  # device has no attribute; use object without it
    obj.memory_settings = SimpleNamespace()
    obj._memory_settings_flags = {"torch_compile_applied": True}
    obj._apply_torch_compile_opt_in()
    obj._apply_torch_compile.assert_called_once_with(False)
    assert obj._memory_settings_flags["torch_compile_applied"] is False
