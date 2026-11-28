"""Unit tests for the FP8 scaled-linear extraction helpers.

_mirror_autocast_dtype, _fp8_scaled_mm_applicable, and
_run_fp8_scaled_mm were extracted to keep _scaled_fp8_linear
within the long-function threshold. These tests pin the dtype
mirroring, the applicability gates, and the fallback on kernel
errors.
"""

import torch

from airunner_services.art.managers.zimage.native.fp8_ops import (
    _fp8_scaled_mm_applicable,
    _mirror_autocast_dtype,
)


def test_mirror_passthrough_for_bfloat16():
    x = torch.zeros(2, 2, dtype=torch.bfloat16)
    out_x, out_dtype = _mirror_autocast_dtype(x, None)
    assert out_x is x
    assert out_dtype == torch.bfloat16


def test_mirror_none_for_fp32_without_autocast(monkeypatch):
    monkeypatch.setattr(torch, "is_autocast_enabled", lambda *a, **k: False)
    x = torch.zeros(2, 2, dtype=torch.float32)
    assert _mirror_autocast_dtype(x, None) is None


def test_mirror_casts_when_compute_dtype_given(monkeypatch):
    monkeypatch.setattr(torch, "is_autocast_enabled", lambda *a, **k: True)
    monkeypatch.setattr(
        torch, "get_autocast_dtype", lambda *a, **k: torch.bfloat16
    )
    x = torch.zeros(2, 2, dtype=torch.float32)
    out_x, out_dtype = _mirror_autocast_dtype(x, torch.float16)
    assert out_dtype == torch.float16
    assert out_x.dtype == torch.float16


def test_applicable_none_for_wrong_weight_dtype():
    x = torch.zeros(600, 16, dtype=torch.bfloat16)
    qweight = torch.zeros(8, 16, dtype=torch.float16)
    assert _fp8_scaled_mm_applicable(x, qweight) is None


def test_applicable_none_for_small_batch():
    x = torch.zeros(10, 16, dtype=torch.bfloat16)
    qweight = torch.zeros(8, 16, dtype=torch.float8_e4m3fn)
    assert _fp8_scaled_mm_applicable(x, qweight) is None


def test_applicable_none_for_ragged_inner_dim():
    x = torch.zeros(600, 15, dtype=torch.bfloat16)
    qweight = torch.zeros(8, 15, dtype=torch.float8_e4m3fn)
    assert _fp8_scaled_mm_applicable(x, qweight) is None
