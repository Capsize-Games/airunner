"""Transformer-loading helpers for the native Z-Image pipeline."""

from __future__ import annotations

import gc
import logging
from typing import Dict, Optional

import torch
import torch.nn as nn
from safetensors import safe_open

from airunner_services.art.managers.zimage.native.fp8_ops import (
    FP8Linear,
)
from airunner_services.art.managers.zimage.native.nextdit_model import (
    NextDiT,
    ZIMAGE_CONFIG,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_transformer_direct_helper import (
    ZImageNativePipelineTransformerDirectHelper,
)

logger = logging.getLogger(__name__)


class ZImageNativePipelineTransformerLoaderHelper:
    """Load transformer checkpoints into the native pipeline."""

    def __init__(self, owner) -> None:
        """Store the owning native pipeline."""
        self._owner = owner
        self._direct_helper = ZImageNativePipelineTransformerDirectHelper(owner)

    def load_transformer(
        self,
        checkpoint_path: Optional[str] = None,
        stream_load: bool = True,
    ) -> None:
        """Load the pipeline transformer from one checkpoint path."""
        path = checkpoint_path or self._owner.transformer_path
        if path is None:
            raise ValueError("No transformer path provided")
        logger.info("Loading transformer from %s", path)
        support = self._owner._get_transformer_support()
        self._owner.is_fp8, self._owner._is_unscaled_fp8 = (
            support.inspect_checkpoint_mode(path)
        )
        if self._owner.is_fp8 and stream_load:
            self.load_fp8_checkpoint_streaming(path)
        else:
            self.load_checkpoint_direct(path)
        self._owner._loaded_components.append("transformer")
        logger.info("Transformer loaded successfully")

    def load_fp8_checkpoint_streaming(self, path: str) -> None:
        """Stream one scaled FP8 checkpoint into the transformer."""
        support = self._owner._get_transformer_support()
        n_layers = support.detect_layer_count(path)
        logger.info("Detected %s layers in checkpoint", n_layers)
        self._owner.transformer = NextDiT(
            **self._model_config(n_layers),
            device=torch.device("meta"),
            dtype=self._owner.dtype,
        )
        scale_dict, all_weights = self._collect_fp8_checkpoint_tensors(path)
        fp8_layers = self._build_fp8_layer_map(scale_dict, all_weights)
        del all_weights
        gc.collect()
        self._replace_fp8_layers(fp8_layers)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self._owner.transformer.eval()

    def _model_config(self, n_layers: int) -> Dict[str, int]:
        """Return a model config adjusted for the current layer count."""
        model_config = ZIMAGE_CONFIG.copy()
        if n_layers != model_config.get("n_layers", 32):
            logger.info(
                "Overriding n_layers from %s to %s",
                model_config.get("n_layers", 32),
                n_layers,
            )
            model_config["n_layers"] = n_layers
        return model_config

    @staticmethod
    def _collect_fp8_checkpoint_tensors(
        path: str,
    ) -> tuple[Dict[str, torch.Tensor], Dict[str, torch.Tensor]]:
        """Collect scales and tensors from one scaled FP8 checkpoint."""
        scale_dict: Dict[str, torch.Tensor] = {}
        all_weights: Dict[str, torch.Tensor] = {}
        with safe_open(path, framework="pt") as checkpoint:
            keys = list(checkpoint.keys())
            for key in keys:
                if "scale_weight" in key:
                    scale_dict[key] = checkpoint.get_tensor(key)
            logger.info("Found %s scale weights", len(scale_dict))
            for key in keys:
                if "scale_weight" not in key:
                    all_weights[key] = checkpoint.get_tensor(key)
        return scale_dict, all_weights

    def _build_fp8_layer_map(
        self,
        scale_dict: Dict[str, torch.Tensor],
        all_weights: Dict[str, torch.Tensor],
    ) -> Dict[str, tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]]:
        """Build one FP8 layer map and materialize non-FP8 weights."""
        fp8_layers, bias_dict = self._collect_fp8_layers(
            scale_dict,
            all_weights,
        )
        self._attach_fp8_biases(fp8_layers, bias_dict)
        linked = sum(1 for layer in fp8_layers.values() if layer[2] is not None)
        logger.info(
            "Found %s biases, %s associated with FP8 layers",
            len(bias_dict),
            linked,
        )
        return fp8_layers

    def _collect_fp8_layers(
        self,
        scale_dict: Dict[str, torch.Tensor],
        all_weights: Dict[str, torch.Tensor],
    ) -> tuple[
        Dict[str, tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]],
        Dict[str, torch.Tensor],
    ]:
        """Collect FP8 layer tuples and deferred bias tensors."""
        support = self._owner._get_transformer_support()
        fp8_layers = {}
        bias_dict = {}
        for key, tensor in all_weights.items():
            self._collect_fp8_tensor(
                support,
                scale_dict,
                fp8_layers,
                bias_dict,
                key,
                tensor,
            )
        return fp8_layers, bias_dict

    def _collect_fp8_tensor(
        self,
        support,
        scale_dict: Dict[str, torch.Tensor],
        fp8_layers: Dict[str, tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]],
        bias_dict: Dict[str, torch.Tensor],
        key: str,
        tensor: torch.Tensor,
    ) -> None:
        """Classify one checkpoint tensor as FP8, bias, or regular weight."""
        model_key = support.convert_checkpoint_key(key)
        if model_key is None:
            return
        if key.endswith(".bias"):
            bias_dict[model_key.rsplit(".", 1)[0]] = tensor
            return
        scale = scale_dict.get(key.replace(".weight", ".scale_weight"))
        if self._store_fp8_layer(fp8_layers, model_key, tensor, scale):
            return
        self._materialize_tensor(model_key, tensor)

    @staticmethod
    def _store_fp8_layer(
        fp8_layers: Dict[str, tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]],
        model_key: str,
        tensor: torch.Tensor,
        scale: Optional[torch.Tensor],
    ) -> bool:
        """Store one FP8 layer tuple when the checkpoint tensor qualifies."""
        if tensor.dtype != torch.float8_e4m3fn or scale is None:
            return False
        if not model_key.endswith(".weight"):
            return False
        fp8_layers[model_key.rsplit(".", 1)[0]] = (tensor, scale, None)
        return True

    @staticmethod
    def _attach_fp8_biases(
        fp8_layers: Dict[str, tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]],
        bias_dict: Dict[str, torch.Tensor],
    ) -> None:
        """Attach deferred bias tensors to their matching FP8 layers."""
        for layer_key, bias in bias_dict.items():
            if layer_key not in fp8_layers:
                continue
            fp8_weight, scale, _ = fp8_layers[layer_key]
            fp8_layers[layer_key] = (fp8_weight, scale, bias)

    def _materialize_tensor(self, model_key: str, tensor: torch.Tensor) -> None:
        """Materialize one non-FP8 tensor directly on the target device."""
        support = self._owner._get_transformer_support()
        try:
            support.set_module_tensor_to_device(
                self._owner.transformer,
                model_key,
                self._owner.device,
                tensor.to(dtype=self._owner.dtype),
            )
        except Exception as exc:
            logger.debug("Could not set %s: %s", model_key, exc)

    def _replace_fp8_layers(
        self,
        fp8_layers: Dict[str, tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]],
    ) -> None:
        """Replace linear layers with FP8Linear modules."""
        replaced = 0
        for layer_key, layer_data in fp8_layers.items():
            if self._replace_one_fp8_layer(layer_key, *layer_data):
                replaced += 1
        logger.info("Replaced %s Linear layers with FP8Linear", replaced)

    def _replace_one_fp8_layer(
        self,
        layer_key: str,
        fp8_weight: torch.Tensor,
        scale: torch.Tensor,
        bias: Optional[torch.Tensor],
    ) -> bool:
        """Replace one linear layer with an FP8Linear module."""
        try:
            support = self._owner._get_transformer_support()
            parent = support.resolve_module(
                self._owner.transformer,
                layer_key.split(".")[:-1],
            )
            layer_name = layer_key.split(".")[-1]
            linear = getattr(parent, layer_name)
            if not isinstance(linear, nn.Linear) and not hasattr(
                linear,
                "in_features",
            ):
                return False
            fp8_linear = FP8Linear(
                fp8_weight.shape[1],
                fp8_weight.shape[0],
                bias=bias is not None,
                device=self._owner.device,
                compute_dtype=self._owner.dtype,
            )
            fp8_linear.set_fp8_weight(
                fp8_weight.to(self._owner.device),
                scale.to(self._owner.device),
            )
            if bias is not None:
                fp8_linear.bias.data.copy_(
                    bias.to(dtype=self._owner.dtype, device=self._owner.device)
                )
            setattr(parent, layer_name, fp8_linear)
            return True
        except Exception as exc:
            logger.warning(
                "Failed to replace %s with FP8Linear: %s",
                layer_key,
                exc,
            )
            return False

    def load_checkpoint_direct(self, path: str) -> None:
        """Load one direct checkpoint into the transformer."""
        self._direct_helper.load_checkpoint_direct(path)