"""Transformer fallback helpers for Z-Image single-file loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from diffusers import BitsAndBytesConfig as DiffusersBnBConfig
from safetensors.torch import load_file as load_safetensors
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from airunner_services.art.pipelines.z_image import ZImageTransformer2DModel


class ZImageSingleFileTransformerHelper:
    """Load transformer and local text assets for single-file fallback."""

    def __init__(self, owner) -> None:
        """Store the owning single-file loader helper."""
        self._owner = owner

    def build_transformer_quantization_config(
        self,
        use_quant: bool,
        quant_bits: Optional[int],
    ) -> Optional[DiffusersBnBConfig]:
        """Create one transformer quantization config for fallback loads."""
        if use_quant and quant_bits == 4:
            return DiffusersBnBConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        if use_quant and quant_bits == 8:
            return DiffusersBnBConfig(load_in_8bit=True)
        return None

    def load_transformer_for_fallback(
        self,
        model_dir: str,
        model_path: str,
        transformer_cfg: Optional[DiffusersBnBConfig],
        model_dtype: torch.dtype,
        max_memory: Optional[dict],
        quant_bits: Optional[int],
        pretrained_helper,
    ) -> Any:
        """Load one transformer for the manual single-file fallback path."""
        if transformer_cfg is not None:
            self._owner._owner.logger.info(
                "Fallback: loading transformer from pretrained with %s-bit "
                "quantization",
                quant_bits,
            )
            transformer = pretrained_helper.load_transformer_from_pretrained(
                Path(os.path.join(model_dir, "transformer")),
                transformer_cfg,
                model_dtype,
                max_memory,
            )
            if transformer is not None:
                return transformer
            self._owner._owner.logger.warning(
                "Quantized transformer load failed; falling back to "
                "safetensors weights"
            )
        transformer = self.create_transformer_from_config_or_default(model_dir)
        self._owner._owner.logger.info(
            "Loading transformer weights from %s",
            model_path,
        )
        self.load_transformer_weights_from_safetensors(transformer, model_path)
        transformer = transformer.to(model_dtype)
        self._owner._owner.logger.info(
            "Transformer loaded successfully (dtype: %s)",
            model_dtype,
        )
        return transformer

    def load_local_text_encoder(
        self,
        model_dir: str,
        model_dtype: torch.dtype,
    ) -> tuple[Any, Any]:
        """Load local text-encoder assets when the caller did not supply them."""
        text_encoder_path = os.path.join(model_dir, "text_encoder")
        tokenizer_path = os.path.join(model_dir, "tokenizer")
        self._owner._owner.logger.info(
            "Loading text encoder from %s",
            text_encoder_path,
        )
        text_encoder = AutoModelForCausalLM.from_pretrained(
            text_encoder_path,
            torch_dtype=model_dtype,
            local_files_only=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_path,
            local_files_only=True,
        )
        return text_encoder, tokenizer

    def create_transformer_from_config_or_default(self, model_dir: str) -> Any:
        """Create one transformer from disk config or the default Z-Image config."""
        config_path = os.path.join(model_dir, "transformer", "config.json")
        if os.path.exists(config_path):
            self._owner._owner.logger.info(
                "Loading transformer config from %s",
                config_path,
            )
            return ZImageTransformer2DModel.from_config(config_path)
        self._owner._owner.logger.info(
            "No transformer config found, using default Z-Image config"
        )
        return ZImageTransformer2DModel(
            all_patch_size=(2,),
            all_f_patch_size=(1,),
            in_channels=16,
            dim=3840,
            n_layers=30,
            n_refiner_layers=2,
            n_heads=30,
            n_kv_heads=30,
            norm_eps=1e-5,
            qk_norm=True,
            cap_feat_dim=2560,
            rope_theta=256.0,
            t_scale=1000.0,
            axes_dims=[32, 48, 48],
            axes_lens=[1024, 512, 512],
        )

    def load_transformer_weights_from_safetensors(
        self,
        transformer: Any,
        model_path: str,
    ) -> None:
        """Load transformer weights from one safetensors checkpoint."""
        state_dict = load_safetensors(model_path)
        transformer_keys = [
            key
            for key in state_dict.keys()
            if not key.startswith(("vae.", "text_encoder."))
        ]
        transformer_state_dict = (
            {
                key: value
                for key, value in state_dict.items()
                if key in transformer_keys
            }
            if transformer_keys
            else state_dict
        )
        missing, unexpected = transformer.load_state_dict(
            transformer_state_dict,
            strict=False,
        )
        if missing:
            self._owner._owner.logger.warning(
                "Missing keys when loading transformer: %s keys",
                len(missing),
            )
            self._owner._owner.logger.debug(
                "Missing keys: %s...", missing[:10]
            )
        if unexpected:
            self._owner._owner.logger.warning(
                "Unexpected keys when loading transformer: %s keys",
                len(unexpected),
            )
            self._owner._owner.logger.debug(
                "Unexpected keys: %s...",
                unexpected[:10],
            )
