"""Unit tests for the Z-Image component stage helpers.

_load_transformer_stage, _load_encoder_stage, and _load_vae_stage
were extracted to keep _load_components within the long-function
threshold. These tests pin the stage wiring, capacity checks, and
the None-failure errors.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from airunner_services.art.managers.zimage.mixins.zimage_pretrained_loader_helper import (
    ZImagePretrainedLoaderHelper,
)


def _make_helper():
    helper = ZImagePretrainedLoaderHelper.__new__(
        ZImagePretrainedLoaderHelper
    )
    helper._owner = MagicMock()
    helper._check_live_capacity = MagicMock()
    return helper


def _plan():
    component = SimpleNamespace(
        estimated_resident_bytes=0,
        source_tensor_bytes=0,
        largest_shard_bytes=0,
        tensor_count=0,
        estimated_resident_gib=0.0,
    )
    plan = SimpleNamespace(
        transformer=component,
        text_encoder=component,
        vae=component,
        gpu_weight_budget_gib=1.0,
        cpu_weight_budget_gib=2.0,
        cpu_workspace_gib=3.0,
        gpu_activation_reserve_gib=0.5,
        text_encoder_gpu_gib=1.0,
        text_encoder_cpu_gib=1.0,
        vae_gpu_gib=1.0,
        vae_cpu_gib=1.0,
        max_memory_transformer={},
        max_memory_text_encoder={},
    )
    return plan


def test_transformer_stage_loads_and_returns():
    helper = _make_helper()
    helper.load_transformer_from_pretrained = MagicMock(return_value="tr")
    out = helper._load_transformer_stage(
        Path("/m"), "cfg", "fp16", _plan(), "q"
    )
    assert out == "tr"
    helper._check_live_capacity.assert_not_called()


def test_transformer_stage_raises_on_none():
    helper = _make_helper()
    helper.load_transformer_from_pretrained = MagicMock(return_value=None)
    with pytest.raises(RuntimeError, match="Failed to load transformer"):
        helper._load_transformer_stage(
            Path("/m"), "cfg", "fp16", _plan(), "q"
        )


def test_encoder_stage_checks_capacity_and_loads():
    helper = _make_helper()
    helper.load_text_encoder_from_pretrained = MagicMock(return_value=("te", "tok"))
    plan = _plan()
    te, tok = helper._load_encoder_stage(Path("/m"), "cfg", "fp16", plan, "q")
    assert (te, tok) == ("te", "tok")
    helper._check_live_capacity.assert_called_once()
    assert helper._check_live_capacity.call_args[0][0] == "text encoder"


def test_encoder_stage_raises_on_none():
    helper = _make_helper()
    helper.load_text_encoder_from_pretrained = MagicMock(return_value=(None, "tok"))
    with pytest.raises(RuntimeError, match="Failed to load text encoder"):
        helper._load_encoder_stage(Path("/m"), "cfg", "fp16", _plan(), "q")


def test_vae_stage_runs_two_capacity_checks():
    helper = _make_helper()
    helper.load_vae_from_pretrained = MagicMock(return_value="vae")
    plan = _plan()
    assert helper._load_vae_stage(Path("/m"), "fp16", plan, False) == "vae"
    assert helper._check_live_capacity.call_count == 2
    labels = [c[0][0] for c in helper._check_live_capacity.call_args_list]
    assert labels == ["VAE", "VAE placement"]


def test_vae_stage_raises_on_none():
    helper = _make_helper()
    helper.load_vae_from_pretrained = MagicMock(return_value=None)
    with pytest.raises(RuntimeError, match="Failed to load VAE"):
        helper._load_vae_stage(Path("/m"), "fp16", _plan(), True)
