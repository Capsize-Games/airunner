"""Direct-load FP8 scale handling for the native Z-Image transformer."""

from __future__ import annotations

from types import SimpleNamespace

import torch
import torch.nn as nn
from safetensors.torch import save_file

from airunner_services.art.managers.zimage.native.zimage_native_pipeline_transformer_direct_helper import (
    ZImageNativePipelineTransformerDirectHelper,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_transformer_support import (
    ZImageNativePipelineTransformerSupport,
)

_LAYER = "layers.0.test_linear"
_FP8_VALUES = [[1.0, -2.0], [0.5, 4.0]]


class _FakeOwner:
    """Minimal pipeline owner for direct-helper tests."""

    def __init__(self, transformer=None) -> None:
        self.device = torch.device("cpu")
        self.dtype = torch.bfloat16
        self.transformer = transformer
        self._support = ZImageNativePipelineTransformerSupport(self)

    def _get_transformer_support(self) -> ZImageNativePipelineTransformerSupport:
        return self._support


def _fp8_weight() -> torch.Tensor:
    return torch.tensor(_FP8_VALUES, dtype=torch.float32).to(torch.float8_e4m3fn)


def _expected(scale: float) -> torch.Tensor:
    return (torch.tensor(_FP8_VALUES, dtype=torch.float32) * scale).to(
        torch.bfloat16
    )


def _load_scaled(tmp_path, scale_key: str, scale: float):
    path = tmp_path / "checkpoint.safetensors"
    save_file(
        {
            f"{_LAYER}.weight": _fp8_weight(),
            f"{_LAYER}.bias": torch.tensor([0.25, -0.75], dtype=torch.float32),
            f"{_LAYER}.{scale_key}": torch.tensor(scale, dtype=torch.float32),
        },
        str(path),
    )
    owner = _FakeOwner()
    helper = ZImageNativePipelineTransformerDirectHelper(owner)
    fp8_layers, non_fp8_weights = helper._collect_direct_checkpoint_tensors(
        str(path)
    )
    replaced, fp8_non_linear = helper._replace_unscaled_fp8_layers(fp8_layers)
    merged = {**non_fp8_weights, **fp8_non_linear}
    return replaced, merged


def test_weight_scale_dequantizes_and_preserves_bias(tmp_path) -> None:
    """Happy: ComfyUI .weight_scale dequantizes to fp8*scale in owner dtype."""
    replaced, merged = _load_scaled(tmp_path, "weight_scale", 0.5)

    assert replaced == 1
    weight = merged[f"{_LAYER}.weight"]
    assert weight.dtype == torch.bfloat16
    assert torch.equal(weight, _expected(0.5))
    assert torch.equal(
        merged[f"{_LAYER}.bias"],
        torch.tensor([0.25, -0.75], dtype=torch.bfloat16),
    )


def test_scale_weight_dequantizes(tmp_path) -> None:
    """Happy: legacy .scale_weight dequantizes with its scale (pre-fix: dropped)."""
    replaced, merged = _load_scaled(tmp_path, "scale_weight", 2.0)

    assert replaced == 1
    weight = merged[f"{_LAYER}.weight"]
    assert weight.dtype == torch.bfloat16
    assert torch.equal(weight, _expected(2.0))
    assert torch.equal(
        merged[f"{_LAYER}.bias"],
        torch.tensor([0.25, -0.75], dtype=torch.bfloat16),
    )


def test_restore_default_norm_scales_zero_becomes_ones() -> None:
    """Happy: an all-zero norm_final weight is reset to ones."""
    transformer = SimpleNamespace(
        norm_final=SimpleNamespace(weight=nn.Parameter(torch.zeros(4)))
    )
    helper = ZImageNativePipelineTransformerDirectHelper(
        _FakeOwner(transformer=transformer)
    )

    helper._restore_default_norm_scales()

    assert torch.equal(transformer.norm_final.weight.data, torch.ones(4))


def test_restore_default_norm_scales_nonzero_untouched() -> None:
    """Sad: a non-zero norm_final weight is left untouched."""
    original = torch.tensor([0.0, 3.0, 0.0, -1.0])
    transformer = SimpleNamespace(
        norm_final=SimpleNamespace(weight=nn.Parameter(original.clone()))
    )
    helper = ZImageNativePipelineTransformerDirectHelper(
        _FakeOwner(transformer=transformer)
    )

    helper._restore_default_norm_scales()

    assert torch.equal(transformer.norm_final.weight.data, original)


def test_restore_default_norm_scales_missing_norm_final() -> None:
    """Sad: no norm_final does not crash."""
    helper = ZImageNativePipelineTransformerDirectHelper(
        _FakeOwner(transformer=SimpleNamespace())
    )

    helper._restore_default_norm_scales()


def test_convert_checkpoint_key_rejects_comfy_quant() -> None:
    """Bad: comfy_quant metadata keys have no model key."""
    assert (
        ZImageNativePipelineTransformerSupport.convert_checkpoint_key(
            "layers.0.test_linear.comfy_quant"
        )
        is None
    )
    assert (
        ZImageNativePipelineTransformerSupport.convert_checkpoint_key(
            "model.diffusion_model.layers.0.test_linear.weight.comfy_quant"
        )
        is None
    )
