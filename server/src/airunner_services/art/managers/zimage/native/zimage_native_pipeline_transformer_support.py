"""Transformer support helpers for the native Z-Image pipeline."""

from __future__ import annotations

import logging
from typing import Optional, Union

import torch
import torch.nn as nn
from safetensors import safe_open

from airunner_services.art.managers.zimage.native.fp8_ops import (
    QuantizedTensor,
)
from airunner_services.art.managers.zimage.native.nextdit_model import (
    ZIMAGE_CONFIG,
)

logger = logging.getLogger(__name__)


class ZImageNativePipelineTransformerSupport:
    """Shared checkpoint and tensor utilities for transformer loading."""

    def __init__(self, owner) -> None:
        """Store the owning native pipeline."""
        self._owner = owner

    def inspect_checkpoint_mode(self, path: str) -> tuple[bool, bool]:
        """Return whether one checkpoint is scaled or unscaled FP8."""
        if not path.endswith(".safetensors"):
            return False, False
        has_fp8_dtype, has_scale_key = self._scan_checkpoint_mode(path)
        is_fp8 = has_fp8_dtype and has_scale_key
        is_unscaled_fp8 = has_fp8_dtype and not has_scale_key
        if is_unscaled_fp8:
            logger.info(
                "Checkpoint is unscaled FP8 (will cast to %s)",
                self._owner.dtype,
            )
        else:
            logger.info("Checkpoint is FP8 scaled: %s", is_fp8)
        return is_fp8, is_unscaled_fp8

    @staticmethod
    def _scan_checkpoint_mode(path: str) -> tuple[bool, bool]:
        """Return sampled dtype and scale-key presence for one checkpoint."""
        has_fp8_dtype = False
        has_scale_key = False
        with safe_open(path, framework="pt") as checkpoint:
            all_keys = list(checkpoint.keys())
            has_scale_key = any("scale_weight" in key for key in all_keys)
            for index, key in enumerate(all_keys):
                if index > 50:
                    break
                tensor = checkpoint.get_tensor(key)
                if tensor.dtype == torch.float8_e4m3fn:
                    has_fp8_dtype = True
                    break
        return has_fp8_dtype, has_scale_key

    @staticmethod
    def detect_layer_count(path: str) -> int:
        """Detect the number of transformer layers in one checkpoint."""
        layer_nums = set()
        with safe_open(path, framework="pt") as checkpoint:
            for key in checkpoint.keys():
                if "layers." not in key:
                    continue
                parts = key.split(".")
                for index, part in enumerate(parts[:-1]):
                    if part != "layers":
                        continue
                    try:
                        layer_nums.add(int(parts[index + 1]))
                    except ValueError:
                        pass
        return len(layer_nums) or ZIMAGE_CONFIG.get("n_layers", 32)

    @staticmethod
    def convert_checkpoint_key(key: str) -> Optional[str]:
        """Convert one checkpoint key to the model naming scheme."""
        prefixes = [
            "model.diffusion_model.",
            "diffusion_model.",
            "model.",
            "transformer.",
        ]
        for prefix in prefixes:
            if key.startswith(prefix):
                key = key[len(prefix) :]
                break
        if "scale_weight" in key:
            return None
        return key

    def set_module_tensor_to_device(
        self,
        module: nn.Module,
        tensor_name: str,
        device: Union[str, torch.device],
        value: torch.Tensor,
    ) -> None:
        """Set one nested parameter or buffer on a target module."""
        parent = self.resolve_module(module, tensor_name.split(".")[:-1])
        param_name = tensor_name.split(".")[-1]
        if not isinstance(value, QuantizedTensor):
            value = value.to(device)
        if hasattr(parent, param_name):
            delattr(parent, param_name)
        if isinstance(value, QuantizedTensor):
            parent.register_buffer(param_name, value._qdata)
            scale_name = f"{param_name}_scale"
            parent.register_buffer(scale_name, value._layout_params["scale"])
            return
        setattr(parent, param_name, nn.Parameter(value, requires_grad=False))

    def materialize_meta_tensors(self) -> None:
        """Materialize remaining meta tensors on the active device."""
        transformer = self._owner.transformer
        if transformer is None:
            return
        params = self._materialize_meta_parameters(transformer)
        buffers = self._materialize_meta_buffers(transformer)
        if params or buffers:
            logger.debug(
                "Materialized %d meta parameters and %d meta buffers",
                params,
                buffers,
            )

    def _materialize_meta_parameters(self, transformer: nn.Module) -> int:
        """Materialize meta parameters in one transformer."""
        materialized = 0
        for name, param in transformer.named_parameters():
            if param.device.type != "meta":
                continue
            module = self.resolve_module(transformer, name.split(".")[:-1])
            new_param = nn.Parameter(
                torch.zeros(
                    param.shape,
                    device=self._owner.device,
                    dtype=self._owner.dtype,
                ),
                requires_grad=False,
            )
            setattr(module, name.split(".")[-1], new_param)
            materialized += 1
        return materialized

    def _materialize_meta_buffers(self, transformer: nn.Module) -> int:
        """Materialize meta buffers in one transformer."""
        materialized = 0
        for name, buffer in transformer.named_buffers():
            if buffer.device.type != "meta":
                continue
            module = self.resolve_module(transformer, name.split(".")[:-1])
            new_buffer = torch.zeros(
                buffer.shape,
                device=self._owner.device,
                dtype=self._owner.dtype,
            )
            module.register_buffer(name.split(".")[-1], new_buffer)
            materialized += 1
        return materialized

    @staticmethod
    def resolve_module(module: nn.Module, parts: list[str]) -> nn.Module:
        """Walk one dotted module path and return the target module."""
        for part in parts:
            module = (
                module[int(part)] if part.isdigit() else getattr(module, part)
            )
        return module
