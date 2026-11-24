"""Direct transformer checkpoint loading for the native Z-Image pipeline."""

from __future__ import annotations

import gc
import logging
from typing import Dict, Optional

import torch
import torch.nn as nn
from safetensors import safe_open

from airunner_services.art.managers.zimage.native.fp8_ops import (
    FP8Linear,
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
        fp8_layers, non_fp8_weights = self._collect_direct_checkpoint_tensors(path)
        replaced, fp8_non_linear = self._replace_unscaled_fp8_layers(fp8_layers)
        non_fp8_weights.update(fp8_non_linear)
        loaded_other = self._materialize_non_fp8_weights(non_fp8_weights)
        logger.info(
            "Loaded transformer: %s FP8 Linear layers, %s other tensors",
            replaced,
            loaded_other,
        )
        self._owner._get_transformer_support().materialize_meta_tensors()
        self._restore_default_norm_scales()
        self._owner.transformer.eval()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _restore_default_norm_scales(self) -> None:
        """Reset unfitted final-norm scales to ones.

        Some single-file exports omit norm_final.weight (it trains to
        ~1 and adds nothing); meta materialization leaves zeros, which
        would zero the transformer output. Ones match RMSNorm init.
        """
        norm_final = getattr(self._owner.transformer, "norm_final", None)
        weight = getattr(norm_final, "weight", None)
        if isinstance(weight, nn.Parameter) and not bool((weight != 0).any()):
            with torch.no_grad():
                weight.fill_(1.0)

    def _log_direct_vram(self) -> None:
        """Log current VRAM before a direct checkpoint load."""
        if not torch.cuda.is_available():
            return
        allocated = torch.cuda.memory_allocated() / 1024**3
        logger.info(
            "_load_checkpoint_direct: Pre-load VRAM: %.2fGB allocated",
            allocated,
        )

    @staticmethod
    def _fp8_layer_slot(
        fp8_layers: Dict[str, list[Optional[torch.Tensor]]],
        layer_key: str,
    ) -> list[Optional[torch.Tensor]]:
        """Return the [weight, bias, scale] slot for one layer."""
        slot = fp8_layers.setdefault(layer_key, [None, None, None])
        while len(slot) < 3:
            slot.append(None)
        return slot

    def _collect_direct_scale_weight(
        self,
        fp8_layers: Dict[str, list[Optional[torch.Tensor]]],
        support,
        key: str,
        tensor: torch.Tensor,
    ) -> None:
        """Capture one legacy ``.scale_weight`` scale for the direct path.

        ``convert_checkpoint_key`` returns None for this naming (the
        streaming path handles it separately), so derive the layer key
        from the matching ``.weight`` key instead of dropping the scale.
        """
        weight_key = f"{key[: -len('.scale_weight')]}.weight"
        converted = support.convert_checkpoint_key(weight_key)
        if converted is None or not converted.endswith(".weight"):
            return
        layer_key = converted[: -len(".weight")]
        self._fp8_layer_slot(fp8_layers, layer_key)[2] = tensor.to(
            dtype=torch.float32, copy=True
        )

    def _collect_direct_weight_scale(
        self,
        fp8_layers: Dict[str, list[Optional[torch.Tensor]]],
        support,
        key: str,
        tensor: torch.Tensor,
    ) -> None:
        """Capture one ComfyUI ``.weight_scale`` scale for the direct path."""
        weight_key = f"{key[: -len('.weight_scale')]}.weight"
        converted = support.convert_checkpoint_key(weight_key)
        if converted is None or not converted.endswith(".weight"):
            return
        layer_key = converted[: -len(".weight")]
        self._fp8_layer_slot(fp8_layers, layer_key)[2] = tensor.to(
            dtype=torch.float32, copy=True
        )

    def _collect_direct_checkpoint_tensors(
        self,
        path: str,
    ) -> tuple[Dict[str, list[Optional[torch.Tensor]]], Dict[str, torch.Tensor]]:
        """Collect direct-load tensors from one checkpoint."""
        support = self._owner._get_transformer_support()
        fp8_layers: Dict[str, list[Optional[torch.Tensor]]] = {}
        non_fp8_weights: Dict[str, torch.Tensor] = {}
        with safe_open(path, framework="pt") as checkpoint:
            for key in checkpoint.keys():
                if key.endswith(".scale_weight"):
                    self._collect_direct_scale_weight(
                        fp8_layers,
                        support,
                        key,
                        checkpoint.get_tensor(key),
                    )
                    continue
                if key.endswith(".weight_scale"):
                    self._collect_direct_weight_scale(
                        fp8_layers,
                        support,
                        key,
                        checkpoint.get_tensor(key),
                    )
                    continue
                model_key = support.convert_checkpoint_key(key)
                if model_key is None:
                    continue
                tensor = checkpoint.get_tensor(key)
                if tensor.dtype == torch.float8_e4m3fn:
                    self._collect_direct_fp8_tensor(fp8_layers, model_key, tensor)
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
            self._fp8_layer_slot(fp8_layers, layer_key)[0] = tensor.to(
                self._owner.device,
                copy=True,
            )
            return
        if model_key.endswith(".bias"):
            layer_key = model_key[:-5]
            self._fp8_layer_slot(fp8_layers, layer_key)[1] = tensor.to(
                device=self._owner.device,
                dtype=self._owner.dtype,
            )

    def _replace_unscaled_fp8_layers(
        self,
        fp8_layers: Dict[str, list[Optional[torch.Tensor]]],
    ) -> tuple[int, Dict[str, torch.Tensor]]:
        """Replace FP8 linear layers, keeping scaled weights quantized."""
        replaced = 0
        fp8_non_linear: Dict[str, torch.Tensor] = {}
        for layer_key, layer_data in fp8_layers.items():
            if layer_data[0] is None:
                continue
            scale = layer_data[2] if len(layer_data) > 2 else None
            if scale is not None:
                if self._replace_one_scaled_fp8_layer(
                    layer_key,
                    layer_data[0],
                    layer_data[1],
                    scale,
                ):
                    replaced += 1
                    continue
                self._store_scaled_fp8_weight(
                    fp8_non_linear,
                    layer_key,
                    layer_data[0],
                    layer_data[1],
                    scale,
                )
                replaced += 1
                continue
            if self._replace_one_unscaled_fp8_layer(
                layer_key,
                layer_data[0],
                layer_data[1],
                fp8_non_linear,
            ):
                replaced += 1
        fp8_layers.clear()
        return replaced, fp8_non_linear

    def _replace_one_scaled_fp8_layer(
        self,
        layer_key: str,
        weight: torch.Tensor,
        bias: Optional[torch.Tensor],
        scale: torch.Tensor,
    ) -> bool:
        """Replace one scaled FP8 layer with an FP8Linear module."""
        try:
            support = self._owner._get_transformer_support()
            parent = support.resolve_module(
                self._owner.transformer,
                layer_key.split(".")[:-1],
            )
            layer_name = layer_key.split(".")[-1]
            linear = getattr(parent, layer_name, None)
            if linear is None or (
                not isinstance(linear, nn.Linear)
                and not hasattr(linear, "in_features")
            ):
                return False
            fp8_linear = FP8Linear(
                weight.shape[1],
                weight.shape[0],
                bias=bias is not None,
                device=self._owner.device,
                compute_dtype=self._owner.dtype,
            )
            fp8_linear.set_fp8_weight(
                weight.to(self._owner.device),
                scale.to(self._owner.device),
            )
            if bias is not None:
                fp8_linear.bias.data.copy_(
                    bias.to(dtype=self._owner.dtype, device=self._owner.device)
                )
            setattr(parent, layer_name, fp8_linear)
            return True
        except Exception as exc:
            logger.debug("Could not replace scaled %s: %s", layer_key, exc)
            return False

    def _store_scaled_fp8_weight(
        self,
        fp8_non_linear: Dict[str, torch.Tensor],
        layer_key: str,
        weight: torch.Tensor,
        bias: Optional[torch.Tensor],
        scale: torch.Tensor,
    ) -> None:
        """Dequantize one ComfyUI scaled-FP8 weight on CPU.

        The raw FP8 copy lives on CUDA from collection; dequantizing on
        CPU keeps only the final tensor for the materializer, halving
        peak VRAM for scaled checkpoints. The result is stored in the
        owner dtype, so scaled weights occupy full-precision memory
        after a direct load, unlike the streaming path, which keeps
        them quantized in FP8Linear modules.
        """
        dequantized = (
            weight.to(device="cpu", dtype=torch.float32)
            * scale.to(device="cpu")
        ).to(dtype=self._owner.dtype)
        del weight
        fp8_non_linear[f"{layer_key}.weight"] = dequantized
        if bias is not None:
            fp8_non_linear[f"{layer_key}.bias"] = bias

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
                self._store_non_linear_fp8(fp8_non_linear, layer_key, weight, bias)
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
        fp8_non_linear[f"{layer_key}.weight"] = weight.to(dtype=self._owner.dtype)
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