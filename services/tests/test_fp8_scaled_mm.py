"""Regression coverage for the optional FP8 tensor-core linear path."""

from __future__ import annotations

import pytest
torch = pytest.importorskip("torch")
import torch.nn.functional as F  # noqa: E402

from airunner_services.art.managers.zimage.native.fp8_ops import (
    FP8Linear,
    UnscaledFP8Linear,
    _scaled_fp8_linear,
)  # noqa: E402


def test_fp8_linear_returns_to_existing_path_on_cpu() -> None:
    x = torch.randn(16, 64, dtype=torch.bfloat16)
    weight = torch.randn(128, 64).to(torch.float8_e4m3fn)
    bias = torch.randn(128, dtype=torch.bfloat16)

    assert _scaled_fp8_linear(x, weight, None, None) is None
    unscaled_layer = UnscaledFP8Linear(64, 128, compute_dtype=torch.bfloat16)
    unscaled_layer.set_weight(weight, bias)
    torch.testing.assert_close(
        unscaled_layer(x), F.linear(x, weight.to(x.dtype), bias)
    )

    scaled_layer = FP8Linear(64, 128, compute_dtype=torch.bfloat16)
    scale = torch.tensor(0.125)
    scaled_layer.set_fp8_weight(weight, scale, orig_dtype=torch.bfloat16)
    scaled_layer.bias = bias
    expected_weight = weight.to(x.dtype) * scale.to(x.dtype)
    torch.testing.assert_close(
        scaled_layer(x), F.linear(x, expected_weight, bias)
    )


@pytest.mark.skipif(not torch.cuda.is_available(), reason="requires CUDA FP8")
@pytest.mark.parametrize("scale_value", [None, 0.125])
def test_fp8_scaled_mm_matches_quantized_activation_reference(scale_value) -> None:
    device = torch.device("cuda")
    generator = torch.Generator(device=device).manual_seed(17)
    x = torch.randn(512, 64, device=device, dtype=torch.bfloat16, generator=generator)
    qweight = (
        torch.randn(128, 64, device=device, generator=generator) * 3
    ).to(torch.float8_e4m3fn)
    bias = torch.randn(128, device=device, dtype=torch.bfloat16, generator=generator)
    scale = (
        torch.tensor(scale_value, device=device, dtype=torch.float32)
        if scale_value is not None
        else None
    )
    fp8_limit = torch.finfo(torch.float8_e4m3fn).max
    scale_a = (x.float().abs().amax() / fp8_limit).clamp_min(1e-12)
    quantized_x = (x.float() / scale_a).to(torch.float8_e4m3fn)
    reconstructed_x = quantized_x.float() * scale_a
    expected_weight = qweight.float()
    if scale is not None:
        expected_weight = expected_weight * scale

    with torch.no_grad():
        small_batch = _scaled_fp8_linear(x[:32], qweight, scale, bias)
        actual = _scaled_fp8_linear(x, qweight, scale, bias)
        if actual is None:
            pytest.skip("this CUDA device or PyTorch build does not support FP8 scaled_mm")
        expected = F.linear(
            reconstructed_x, expected_weight, bias.float()
        ).to(x.dtype)
        if scale is None:
            layer = UnscaledFP8Linear(
                64, 128, compute_dtype=torch.bfloat16
            ).to(device)
            layer.set_weight(qweight, bias)
        else:
            layer = FP8Linear(
                64, 128, compute_dtype=torch.bfloat16
            ).to(device)
            layer.set_fp8_weight(
                qweight, scale, orig_dtype=torch.bfloat16
            )
            layer.bias = bias
        layer_output = layer(x)

    assert small_batch is None
    assert actual.shape == expected.shape == (512, 128)
    torch.testing.assert_close(
        actual.float(), expected.float(), rtol=0.01, atol=0.1
    )
    torch.testing.assert_close(
        layer_output.float(), expected.float(), rtol=0.01, atol=0.1
    )
