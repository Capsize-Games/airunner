"""Unit tests for BaseDiffusersModelManager._initialize_state.

The helper was extracted to keep __init__ within the long-function
threshold. These tests assert the attribute defaults it sets, since a
full manager construction requires a backend.
"""

import pytest

from airunner_services.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner_services.art.runtime_enums import HandlerState


def _make_obj():
    obj = BaseDiffusersModelManager.__new__(BaseDiffusersModelManager)
    obj._initialize_state()
    return obj


def test_memory_flags_defaults():
    obj = _make_obj()
    flags = obj._memory_settings_flags
    assert flags["torch_compile_status"] == "disabled"
    assert flags["tome_ratio"] == 0.0
    assert flags["vae_slicing_applied"] is None
    assert flags["cpu_offload_applied"] is None


def test_state_defaults():
    obj = _make_obj()
    assert obj._pipeline is None
    assert obj._scheduler_name is None
    assert obj.current_scheduler_name == ""
    assert obj.do_change_scheduler is False
    assert obj._resolved_model_version is None
    assert obj._image_request is None
    assert obj._pipe is None
    assert obj.torch_compile_applied is False
    assert obj.torch_compile_status == "disabled"
    assert obj.do_interrupt_image_generation is False
    assert obj._current_state is HandlerState.UNINITIALIZED


def test_prompt_and_image_defaults():
    obj = _make_obj()
    assert obj._current_prompt == ""
    assert obj._current_negative_prompt == ""
    assert obj._current_prompt_2 == ""
    assert obj._current_negative_prompt_2 == ""
    assert obj._prompt_embeds is None
    assert obj._negative_prompt_embeds is None
    assert obj._pooled_prompt_embeds is None
    assert obj._negative_pooled_prompt_embeds is None
    assert obj._generator is None
    assert obj._compel_proc is None
    assert obj._deep_cache_helper is None


def test_cached_properties_defaults():
    obj = _make_obj()
    assert obj._outpaint_image is None
    assert obj._img2img_image is None
    assert obj._drawing_pad_settings is None
    assert obj._outpaint_settings is None
    assert obj._path_settings is None
    assert obj._current_memory_settings is None


def test_initialize_state_is_idempotent():
    obj = _make_obj()
    obj._current_prompt = "a cat"
    obj._initialize_state()
    assert obj._current_prompt == ""
