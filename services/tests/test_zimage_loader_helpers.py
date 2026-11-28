"""Unit tests for the Z-Image pretrained loader helpers.

_get_or_build_memory_plan and _assemble_loaded_pipeline were
extracted to keep load_from_pretrained within the long-function
threshold. These tests pin the plan-cache agreement rule and the
assemble success/failure behavior.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from airunner_services.art.managers.zimage.mixins.zimage_pretrained_loader_helper import (
    ZImagePretrainedLoaderHelper,
)
from airunner_services.art.managers.zimage.zimage_resource_budget import (
    ZImageMemoryPlan,
)


def _plan(bits):
    component = SimpleNamespace(
        estimated_resident_bytes=0,
        source_tensor_bytes=0,
        largest_shard_bytes=0,
        tensor_count=0,
    )
    return ZImageMemoryPlan(
        transformer=component,
        text_encoder=component,
        vae=component,
        gpu_weight_budget_gib=0.0,
        cpu_weight_budget_gib=0.0,
        cpu_workspace_gib=0.0,
        transformer_gpu_gib=0.0,
        transformer_cpu_gib=0.0,
        text_encoder_gpu_gib=0.0,
        text_encoder_cpu_gib=0.0,
        vae_gpu_gib=0.0,
        vae_cpu_gib=0.0,
        gpu_activation_reserve_gib=0.0,
        quantization_bits=bits,
        max_memory_transformer={},
        max_memory_text_encoder={},
    )


def _make_helper(owner=None):
    helper = ZImagePretrainedLoaderHelper.__new__(
        ZImagePretrainedLoaderHelper
    )
    helper._owner = owner or MagicMock()
    helper.build_memory_plan = MagicMock(return_value=_plan(4))
    helper.assemble_pipeline = MagicMock(return_value="pipe-object")
    helper._precision_label = MagicMock(return_value="fp16")
    return helper


def test_matching_cached_plan_reused():
    owner = MagicMock()
    owner._zimage_memory_plan = _plan(4)
    helper = _make_helper(owner)
    plan = helper._get_or_build_memory_plan("/m", True, 4)
    assert plan is owner._zimage_memory_plan
    helper.build_memory_plan.assert_not_called()


def test_mismatched_bits_rebuilds_plan():
    owner = MagicMock()
    owner._zimage_memory_plan = _plan(8)
    helper = _make_helper(owner)
    plan = helper._get_or_build_memory_plan("/m", True, 4)
    helper.build_memory_plan.assert_called_once()
    assert owner._zimage_memory_plan is plan


def test_missing_plan_builds_and_caches():
    owner = MagicMock()
    del owner._zimage_memory_plan
    helper = _make_helper(owner)
    plan = helper._get_or_build_memory_plan("/m", False, None)
    assert owner._zimage_memory_plan is plan
    helper.build_memory_plan.assert_called_once_with(
        "/m", use_quantization=False, quantization_bits=None
    )


def test_assemble_sets_pipe_and_logs():
    owner = MagicMock()
    helper = _make_helper(owner)
    helper._assemble_loaded_pipeline(
        "cls", "tr", "vae", "te", "tok", "sched", False, None, "fp16"
    )
    assert owner._pipe == "pipe-object"
    helper.assemble_pipeline.assert_called_once()


def test_assemble_failure_logs_and_reraises():
    owner = MagicMock()
    helper = _make_helper(owner)
    helper.assemble_pipeline.side_effect = ValueError("boom")
    with pytest.raises(ValueError, match="boom"):
        helper._assemble_loaded_pipeline(
            "cls", "tr", "vae", "te", "tok", "sched", False, None, "fp16"
        )
    owner.logger.error.assert_called_once()
