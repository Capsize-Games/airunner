"""Direct transformer checkpoint loading for the native Z-Image pipeline."""

from __future__ import annotations

import gc
import logging
from typing import Dict, Optional

import torch
import torch.nn as nn
from safetensors import safe_open

from airunner_services.art.managers.zimage.native.fp8_ops import (
    UnscaledFP8Linear,
)
from airunner_services.art.managers.zimage.native.nextdit_model import (
    create_zimage_transformer,
)

logger = logging.getLogger(__name__)


class ZImageNativePipelineTransformerDirectHelper:
    """Load direct transformer checkpoints into the native pipeline."""

    def __init__(self, owner) -> None:
        """Store the owning native pipeline."""
        self._owner = owner

    def load_checkpoint_direct(self, path: str) -> None:
        """Load one direct checkpoint into the transformer."""
        self._log_direct_vram()
        self._owner.transformer = create_zimage_transformer(
            device=torch.device("meta"),
            dtype=self._owner.dtype,
        )
        fp8_layers, non_fp8_weights = self._collect_direct_checkpoint_tensors(
            path
        )
        replaced, fp8_non_linear = self._replace_unscaled_fp8_layers(
            fp8_layers
        )
        non_fp8_weights.update(fp8_non_linear)
        loaded_other = self._materialize_non_fp8_weights(non_fp8_weights)
        logger.info(
            "Loaded transformer: %s FP8 Linear layers, %s other tensors",
            replaced,
            loaded_other,
        )
        self._owner._get_transformer_support().materialize_meta_tensors()
        self._owner.transformer.eval()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _log_direct_vram(self) -> None:
        """Log current VRAM before a direct checkpoint load."""
        if not torch.cuda.is_available():
            return
        allocated = torch.cuda.memory_allocated() / 1024**3
        logger.info(
            "_load_checkpoint_direct: Pre-load VRAM: %.2fGB allocated",
            allocated,
        )

    def _collect_direct_checkpoint_tensors(
        self,
        path: str,
    ) -> tuple[
        Dict[str, list[Optional[torch.Tensor]]], Dict[str, torch.Tensor]
    ]:
        """Collect direct-load tensors from one checkpoint."""
        support = self._owner._get_transformer_support()
        fp8_layers: Dict[str, list[Optional[torch.Tensor]]] = {}
        non_fp8_weights: Dict[str, torch.Tensor] = {}
        with safe_open(path, framework="pt") as checkpoint:
            for key in checkpoint.keys():
                model_key = support.convert_checkpoint_key(key)
                if model_key is None:
                    continue
                tensor = checkpoint.get_tensor(key)
                if tensor.dtype == torch.float8_e4m3fn:
                    self._collect_direct_fp8_tensor(
                        fp8_layers, model_key, tensor
                    )
                else:
                    non_fp8_weights[model_key] = tensor.to(
                        device=self._owner.device,
                        dtype=self._owner.dtype,
                    )
        return fp8_layers, non_fp8_weights

    def _collect_direct_fp8_tensor(
        self,
        fp8_layers: Dict[str, list[Optional[torch.Tensor]]],
        model_key: str,
        tensor: torch.Tensor,
    ) -> None:
        """Collect one FP8 weight or bias for a direct checkpoint load."""
        if model_key.endswith(".weight"):
            layer_key = model_key[:-7]
            fp8_layers.setdefault(layer_key, [None, None])[0] = tensor.to(
                self._owner.device,
                copy=True,
            )
            return
        if model_key.endswith(".bias"):
            layer_key = model_key[:-5]
            fp8_layers.setdefault(layer_key, [None, None])[1] = tensor.to(
                device=self._owner.device,
                dtype=self._owner.dtype,
            )

    def _replace_unscaled_fp8_layers(
        self,
        fp8_layers: Dict[str, list[Optional[torch.Tensor]]],
    ) -> tuple[int, Dict[str, torch.Tensor]]:
        """Replace unscaled FP8 linear layers and collect fallbacks."""
        replaced = 0
        fp8_non_linear: Dict[str, torch.Tensor] = {}
        for layer_key, layer_data in fp8_layers.items():
            if layer_data[0] is None:
                continue
            if self._replace_one_unscaled_fp8_layer(
                layer_key,
                layer_data[0],
                layer_data[1],
                fp8_non_linear,
            ):
                replaced += 1
        return replaced, fp8_non_linear

    def _replace_one_unscaled_fp8_layer(
        self,
        layer_key: str,
        weight: torch.Tensor,
        bias: Optional[torch.Tensor],
        fp8_non_linear: Dict[str, torch.Tensor],
    ) -> bool:
        """Replace one unscaled FP8 linear layer or keep it as fallback."""
        try:
            support = self._owner._get_transformer_support()
            parent = support.resolve_module(
                self._owner.transformer,
                layer_key.split(".")[:-1],
            )
            layer_name = layer_key.split(".")[-1]
            old_layer = getattr(parent, layer_name, None)
            if old_layer is None or not isinstance(old_layer, nn.Linear):
                self._store_non_linear_fp8(
                    fp8_non_linear, layer_key, weight, bias
                )
                return False
            fp8_linear = UnscaledFP8Linear(
                weight.shape[1],
                weight.shape[0],
                bias=bias is not None,
                device=self._owner.device,
                compute_dtype=self._owner.dtype,
            )
            fp8_linear.set_weight(weight, bias)
            setattr(parent, layer_name, fp8_linear)
            return True
        except Exception as exc:
            logger.debug("Could not replace %s: %s", layer_key, exc)
            self._store_non_linear_fp8(fp8_non_linear, layer_key, weight, bias)
            return False

    def _store_non_linear_fp8(
        self,
        fp8_non_linear: Dict[str, torch.Tensor],
        layer_key: str,
        weight: torch.Tensor,
        bias: Optional[torch.Tensor],
    ) -> None:
        """Store FP8 tensors that must be materialized as regular tensors."""
        fp8_non_linear[f"{layer_key}.weight"] = weight.to(
            dtype=self._owner.dtype
        )
        if bias is not None:
            fp8_non_linear[f"{layer_key}.bias"] = bias

    def _materialize_non_fp8_weights(
        self,
        non_fp8_weights: Dict[str, torch.Tensor],
    ) -> int:
        """Materialize non-FP8 checkpoint tensors into the transformer."""
        loaded = 0
        support = self._owner._get_transformer_support()
        for model_key, tensor in non_fp8_weights.items():
            try:
                support.set_module_tensor_to_device(
                    self._owner.transformer,
                    model_key,
                    self._owner.device,
                    tensor,
                )
                loaded += 1
            except Exception as exc:
                logger.debug("Could not set %s: %s", model_key, exc)
        return loaded
